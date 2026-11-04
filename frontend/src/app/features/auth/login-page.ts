import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { AuthService } from '../../core/auth.service';

@Component({
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './login-page.html',
  styleUrl: './login-page.scss',
})
export class LoginPage {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  readonly passwordVisible = signal(false);
  readonly loading = signal(false);
  readonly errorMessage = signal('');
  readonly expiredNotice = this.route.snapshot.queryParamMap.has('reason');
  readonly currentYear = new Date().getFullYear();

  readonly form = this.fb.nonNullable.group({
    username: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(50)]],
    password: ['', [Validators.required, Validators.minLength(1)]],
  });

  submit(): void {
    this.errorMessage.set('');
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.loading.set(true);
    const { username, password } = this.form.getRawValue();
    this.auth.login(username.trim(), password).pipe(finalize(() => this.loading.set(false))).subscribe({
      next: () => {
        const returnUrl = this.route.snapshot.queryParamMap.get('returnUrl');
        const safeReturnUrl = returnUrl?.startsWith('/admin') ? returnUrl : '/admin';
        void this.router.navigateByUrl(safeReturnUrl);
      },
      error: error => {
        if (error.status === 401) {
          this.errorMessage.set('The username or password is incorrect, or this account is inactive.');
        } else if (error.status === 0) {
          this.errorMessage.set('Could not reach SupportIQ. Check that the service is running and try again.');
        } else {
          this.errorMessage.set(error.error?.detail || 'Sign in failed. Please try again.');
        }
      },
    });
  }
}
