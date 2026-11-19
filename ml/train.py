"""Fine-tune the multi-task scam model on the locally generated synthetic set.

    python ml/gen_synthetic.py --n 6000
    python ml/train.py [--base xlm-roberta-base] [--epochs 3] [--out models/scam-bert]

Multi-task: per-message multi-label red flags + per-thread scam type, one shared encoder.
After training: temperature scaling on a held-out dev split (calibration) and per-flag
thresholds; both stored in meta.json and used by scam_detector.model at inference.
The official Validation Set is never read here.
"""
import argparse
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as Fn
from transformers import AutoTokenizer, get_linear_schedule_with_warmup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "detector"))
from scam_detector.model import MODEL_FLAGS, TYPES, build_network, message_inputs, thread_input  # noqa: E402


def make_examples(scen):
    """-> list of dicts: {text, pair, flags (vec|None), type (idx|-100)}"""
    ex = []
    by_n = {m["n"]: set(m.get("flags") or []) for m in scen["messages"]}
    for n, t, p in message_inputs(scen):
        vec = [1.0 if f in by_n.get(n, set()) else 0.0 for f in MODEL_FLAGS]
        ex.append({"text": t, "pair": p, "flags": vec, "type": -100})
    ex.append({"text": thread_input(scen), "pair": None, "flags": None, "type": TYPES.index(scen["scam_type"])})
    return ex


def collate(tok, batch, max_len):
    msg = [b for b in batch if b["flags"] is not None]
    thr = [b for b in batch if b["flags"] is None]
    out = {}
    if msg:
        out["msg"] = (tok([b["text"] for b in msg], [b["pair"] for b in msg], truncation=True, max_length=max_len,
                          padding=True, return_tensors="pt"), torch.tensor([b["flags"] for b in msg]))
    if thr:
        out["thr"] = (tok([b["text"] for b in thr], truncation=True, max_length=256, padding=True, return_tensors="pt"),
                      torch.tensor([b["type"] for b in thr]))
    return out


def run_batches(net, tok, data, bs, max_len, device):
    """Inference -> (flag_logits, flag_labels, type_logits, type_labels) as numpy arrays."""
    net.eval()
    fl, fy, tl, ty = [], [], [], []
    with torch.inference_mode():
        for i in range(0, len(data), bs):
            b = collate(tok, data[i:i + bs], max_len)
            with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=device == "cuda"):
                if "msg" in b:
                    enc, y = b["msg"]
                    lo, _ = net(enc["input_ids"].to(device), enc["attention_mask"].to(device))
                    fl.append(lo.float().cpu())
                    fy.append(y)
                if "thr" in b:
                    enc, y = b["thr"]
                    _, lo = net(enc["input_ids"].to(device), enc["attention_mask"].to(device))
                    tl.append(lo.float().cpu())
                    ty.append(y)
    return torch.cat(fl), torch.cat(fy), torch.cat(tl), torch.cat(ty)


def fit_temperature(loss_fn, logits, labels):
    best_t, best = 1.0, float("inf")
    for t in np.linspace(0.5, 5.0, 46):
        v = float(loss_fn(logits / t, labels))
        if v < best:
            best_t, best = float(t), v
    return best_t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "ml" / "data" / "synth.jsonl"))
    ap.add_argument("--base", default="xlm-roberta-base")
    ap.add_argument("--out", default=str(ROOT / "models" / "scam-bert"))
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--bs", type=int, default=32)
    ap.add_argument("--lr", type=float, default=3e-5)
    ap.add_argument("--max-len", type=int, default=160)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()

    random.seed(a.seed)
    np.random.seed(a.seed)
    torch.manual_seed(a.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    scen = [json.loads(l) for l in open(a.data, encoding="utf-8")]
    random.shuffle(scen)
    n_dev = max(50, len(scen) // 10)
    dev_s, train_s = scen[:n_dev], scen[n_dev:]
    train = [e for s in train_s for e in make_examples(s)]
    dev = [e for s in dev_s for e in make_examples(s)]
    print(f"device={device} train_examples={len(train)} dev_examples={len(dev)}")

    tok = AutoTokenizer.from_pretrained(a.base)
    net = build_network(a.base, len(MODEL_FLAGS), len(TYPES)).to(device)
    opt = torch.optim.AdamW(net.parameters(), lr=a.lr, weight_decay=0.01)
    steps = a.epochs * ((len(train) + a.bs - 1) // a.bs)
    sch = get_linear_schedule_with_warmup(opt, int(0.06 * steps), steps)
    scaler = torch.amp.GradScaler(enabled=device == "cuda")

    # positive weighting for rare flags
    y = np.array([e["flags"] for e in train if e["flags"] is not None])
    pos = y.mean(0).clip(1e-3, None)
    pos_w = torch.tensor(((1 - pos) / pos) ** 0.5, dtype=torch.float32, device=device)

    t0 = time.time()
    for ep in range(a.epochs):
        net.train()
        random.shuffle(train)
        tot = 0.0
        for i in range(0, len(train), a.bs):
            b = collate(tok, train[i:i + a.bs], a.max_len)
            loss = torch.zeros((), device=device)
            with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=device == "cuda"):
                if "msg" in b:
                    enc, yy = b["msg"]
                    lo, _ = net(enc["input_ids"].to(device), enc["attention_mask"].to(device))
                    loss = loss + Fn.binary_cross_entropy_with_logits(lo.float(), yy.to(device), pos_weight=pos_w)
                if "thr" in b:
                    enc, yy = b["thr"]
                    _, lo = net(enc["input_ids"].to(device), enc["attention_mask"].to(device))
                    loss = loss + Fn.cross_entropy(lo.float(), yy.to(device), label_smoothing=0.05)
            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            scaler.step(opt)
            scaler.update()
            sch.step()
            tot += float(loss)
            if (i // a.bs) % 100 == 0:
                print(f"ep {ep} step {i // a.bs} loss {float(loss):.4f}  ({time.time() - t0:.0f}s)", flush=True)
        print(f"epoch {ep} mean loss {tot / max(1, len(train) // a.bs):.4f}")

    # ---- calibration + thresholds on dev
    fl, fy, tl, ty = run_batches(net, tok, dev, 64, a.max_len, device)
    t_flag = fit_temperature(lambda l, y_: Fn.binary_cross_entropy_with_logits(l, y_), fl, fy)
    t_type = fit_temperature(lambda l, y_: Fn.cross_entropy(l, y_), tl, ty)
    pf = torch.sigmoid(fl / t_flag).numpy()
    yf = fy.numpy()
    thresholds, report = {}, {}
    for j, f in enumerate(MODEL_FLAGS):
        best_thr, best_f1 = 0.5, -1
        for thr in np.linspace(0.3, 0.95, 14):
            pr = pf[:, j] >= thr
            tp = float((pr & (yf[:, j] == 1)).sum())
            prec = tp / max(1, pr.sum())
            rec = tp / max(1, (yf[:, j] == 1).sum())
            f1 = 2 * prec * rec / max(1e-9, prec + rec)
            if f1 > best_f1:
                best_thr, best_f1 = float(thr), f1
        thresholds[f] = best_thr
        report[f] = round(best_f1, 4)
    type_acc = float((tl.argmax(-1) == ty).float().mean())
    print(f"dev: temp_flag={t_flag:.2f} temp_type={t_type:.2f} type_acc={type_acc:.4f}")
    print("dev flag F1:", json.dumps(report))

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    net.encoder.save_pretrained(out)
    tok.save_pretrained(out)
    torch.save({"flag_head": net.flag_head.state_dict(), "type_head": net.type_head.state_dict()}, out / "heads.pt")
    meta = {"base": a.base, "flags": MODEL_FLAGS, "types": TYPES, "max_len": a.max_len, "temp_flag": t_flag,
            "temp_type": t_type, "thresholds": thresholds, "dev_flag_f1": report, "dev_type_acc": type_acc,
            "train_scenarios": len(train_s), "epochs": a.epochs, "trained_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    with open(out / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"saved -> {out}  ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
