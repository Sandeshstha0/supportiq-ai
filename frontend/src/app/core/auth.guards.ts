import { isPlatformBrowser } from '@angular/common';
import { inject, PLATFORM_ID } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { map } from 'rxjs';
import { AuthService } from './auth.service';

export const authenticatedGuard: CanActivateFn = (_route, state) => {
  // The bearer token is tab-scoped browser storage and is unavailable to SSR.
  if (!isPlatformBrowser(inject(PLATFORM_ID))) return true;
  const auth = inject(AuthService);
  const router = inject(Router);
  return auth.restoreSession().pipe(map(user => user
    ? true
    : router.createUrlTree(['/admin/login'], { queryParams: { returnUrl: state.url } }),
  ));
};

export const guestOnlyGuard: CanActivateFn = () => {
  if (!isPlatformBrowser(inject(PLATFORM_ID))) return true;
  const auth = inject(AuthService);
  const router = inject(Router);
  return auth.restoreSession().pipe(map(user => user
    ? router.createUrlTree(['/admin'])
    : true,
  ));
};

export const adminRoleGuard: CanActivateFn = () => {
  if (!isPlatformBrowser(inject(PLATFORM_ID))) return true;
  const auth = inject(AuthService);
  const router = inject(Router);
  return auth.restoreSession().pipe(map(user =>
    user?.role === 'admin' ? true : router.createUrlTree(['/admin']),
  ));
};
