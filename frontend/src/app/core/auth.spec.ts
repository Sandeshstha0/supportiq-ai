import { PLATFORM_ID } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, Router, RouterStateSnapshot, UrlTree, provideRouter } from '@angular/router';
import { firstValueFrom, Observable, of } from 'rxjs';
import { authenticatedGuard } from './auth.guards';
import { AuthService } from './auth.service';

describe('staff authentication', () => {
  let router: Router;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideRouter([]), { provide: PLATFORM_ID, useValue: 'browser' }],
    });
  });

  it('redirects an unauthenticated visitor away from protected admin routes', async () => {
    TestBed.overrideProvider(AuthService, { useValue: { restoreSession: () => of(null) } });
    router = TestBed.inject(Router);
    const result = await firstValueFrom(TestBed.runInInjectionContext(() =>
      authenticatedGuard({} as ActivatedRouteSnapshot, { url: '/admin' } as RouterStateSnapshot) as Observable<boolean | UrlTree>,
    ));

    expect(result instanceof UrlTree).toBe(true);
    expect(router.serializeUrl(result as UrlTree)).toContain('/admin/login');
  });

  it('allows a visitor with a valid staff profile through the guard', async () => {
    TestBed.overrideProvider(AuthService, {
      useValue: { restoreSession: () => of({ id: 1, username: 'staff', email: 'staff@example.test', role: 'staff', is_active: true }) },
    });
    router = TestBed.inject(Router);
    const result = await firstValueFrom(TestBed.runInInjectionContext(() =>
      authenticatedGuard({} as ActivatedRouteSnapshot, { url: '/admin' } as RouterStateSnapshot) as Observable<boolean | UrlTree>,
    ));

    expect(result).toBe(true);
  });

  it('clears the tab token and profile on logout', () => {
    const auth = TestBed.inject(AuthService);
    window.sessionStorage.setItem('supportiq_staff_token', 'test-token');
    auth.currentUser.set({ id: 1, username: 'staff', email: 'staff@example.test', role: 'staff', is_active: true });

    auth.logout();

    expect(window.sessionStorage.getItem('supportiq_staff_token')).toBeNull();
    expect(auth.currentUser()).toBeNull();
  });
});
