
import { Component, signal } from '@angular/core';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [],
  templateUrl: './sidebar.html',
  styleUrl: './sidebar.scss'
})
export class Sidebar {

  collapsed = signal(false);

  toggleSidebar(): void {
    this.collapsed.update(value => !value);
  }

}
