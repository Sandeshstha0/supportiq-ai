import { PLATFORM_ID } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, Router, RouterStateSnapshot, UrlTree, provideRouter } from '@angular/router';
import { firstValueFrom, Observable, of } from 'rxjs';
import { adminRoleGuard, authenticatedGuard } from './auth.guards';
import { AuthService } from './auth.service';
import { LoginPage } from '../features/auth/login-page';

describe('staff authentication', () => {
  let router: Router;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [LoginPage],
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

  it('restricts the staff management route to admin users', async () => {
    TestBed.overrideProvider(AuthService, {
      useValue: { restoreSession: () => of({ id: 2, username: 'agent', email: 'agent@example.test', role: 'staff', is_active: true }) },
    });
    router = TestBed.inject(Router);
    const result = await firstValueFrom(TestBed.runInInjectionContext(() =>
      adminRoleGuard({} as ActivatedRouteSnapshot, {} as RouterStateSnapshot) as Observable<boolean | UrlTree>,
    ));

    expect(result instanceof UrlTree).toBe(true);
    expect(router.serializeUrl(result as UrlTree)).toBe('/admin');
  });

  it('allows admin users through the staff management role guard', async () => {
    TestBed.overrideProvider(AuthService, {
      useValue: { restoreSession: () => of({ id: 1, username: 'owner', email: 'owner@example.test', role: 'admin', is_active: true }) },
    });
    router = TestBed.inject(Router);
    const result = await firstValueFrom(TestBed.runInInjectionContext(() =>
      adminRoleGuard({} as ActivatedRouteSnapshot, {} as RouterStateSnapshot) as Observable<boolean | UrlTree>,
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

  it('redirects a successful login directly to the dashboard route', () => {
    TestBed.overrideProvider(AuthService, {
      useValue: { login: () => of({ id: 1, username: 'agent', email: 'agent@example.test', role: 'staff', is_active: true }) },
    });
    const loginPage = TestBed.createComponent(LoginPage).componentInstance;
    router = TestBed.inject(Router);
    const navigation = vi.spyOn(router, 'navigateByUrl').mockResolvedValue(true);
    loginPage.form.setValue({ username: 'agent', password: 'valid-password' });

    loginPage.submit();

    expect(navigation).toHaveBeenCalledWith('/admin');
  });
});
