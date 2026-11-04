import { BootstrapContext, bootstrapApplication } from '@angular/platform-browser';
import { AppShell } from './app/core/app-shell';
import { config } from './app/app.config.server';

const bootstrap = (context: BootstrapContext) =>
    bootstrapApplication(AppShell, config, context);

export default bootstrap;
