import { Component, inject, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { MessageModule } from 'primeng/message';
import { SelectButtonModule } from 'primeng/selectbutton';
import { TagModule } from 'primeng/tag';
import { AuthService } from '../../services/auth.service';
import { UiLang } from '../../services/ui-lang';
import { UiPipe } from '../../services/ui.pipe';

@Component({
  selector: 'app-login-view',
  imports: [UiPipe, FormsModule, ButtonModule, InputTextModule, MessageModule, SelectButtonModule, TagModule],
  templateUrl: './login-view.html',
  styleUrl: './login-view.scss',
})
export class LoginView {
  private readonly auth = inject(AuthService);
  protected readonly lang = inject(UiLang);
  protected readonly langs = [
    { label: 'RO', value: 'ro' },
    { label: 'EN', value: 'en' },
  ];
  readonly authenticated = output<void>();

  protected readonly mode = signal<'login' | 'register'>('login');
  protected readonly username = signal('');
  protected readonly password = signal('');
  protected readonly displayName = signal('');
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly demoAccounts = [
    { username: 'admin', password: 'admin', role: 'admin' as const, label: 'Admin (vede toate datele)' },
    { username: 'user', password: 'user', role: 'user' as const, label: 'User (doar datele proprii)' },
    { username: 'maria', password: 'maria123', role: 'user' as const, label: 'Maria (alt cont de user)' },
  ];

  protected async submit(): Promise<void> {
    const u = this.username().trim();
    const p = this.password();
    if (!u || !p || this.busy()) return;
    this.busy.set(true);
    this.error.set(null);
    try {
      if (this.mode() === 'login') {
        await this.auth.login(u, p);
      } else {
        await this.auth.register(u, p, this.displayName().trim() || undefined);
      }
      this.authenticated.emit();
    } catch (e) {
      this.error.set(e instanceof Error ? e.message : 'Autentificarea a eșuat.');
    } finally {
      this.busy.set(false);
    }
  }

  protected async quickLogin(username: string, password: string): Promise<void> {
    this.mode.set('login');
    this.username.set(username);
    this.password.set(password);
    await this.submit();
  }
}
