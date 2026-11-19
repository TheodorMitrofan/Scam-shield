import { Component, inject } from '@angular/core';
import { CHANNEL_LABEL, Channel, Scenario } from '../../models/scenario';
import { ScenarioStore } from '../../services/scenario-store';

const ICON: Record<Channel, string> = {
  sms: '💬',
  whatsapp: '🟢',
  email: '✉️',
  chat: '🛒',
  call_transcript: '📞',
};

@Component({
  selector: 'app-scenario-list',
  templateUrl: './scenario-list.html',
  styleUrl: './scenario-list.scss',
})
export class ScenarioList {
  protected readonly store = inject(ScenarioStore);
  protected readonly icon = ICON;
  protected readonly label = CHANNEL_LABEL;

  protected who(s: Scenario): string {
    return s.sender.name ?? s.sender.address ?? 'Necunoscut';
  }
}
