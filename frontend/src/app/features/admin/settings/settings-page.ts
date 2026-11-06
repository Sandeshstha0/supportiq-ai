
import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

type SettingsTab =
  | 'general'
  | 'ai'
  | 'support'
  | 'delivery'
  | 'email'
  | 'security';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './settings-page.html',
  styleUrl: './settings-page.scss',
})
export class SettingsComponent {
  activeTab: SettingsTab = 'general';
  saved = false;

  settings = {
    storeName: 'Lasata Department Stores',
    email: 'support@lasata.com.np',
    phone: '9812345678',
    address: 'Vyas Municipality, Tanahun, Nepal',

    assistantName: 'SupportIQ AI',
    welcomeMessage: 'Hello! Welcome to Lasata. How can I help you today?',
    responseStyle: 'Friendly and Professional',
    language: 'English and Nepali',
    aiEnabled: true,

    supportHours: '9:00 AM - 6:00 PM',
    autoTicket: true,
    humanHandoff: true,

    homeDelivery: true,
    deliveryWards: '2, 3, 4',
    deliveryArea: 'Byas, Damauli',

    emailNotifications: true,
    ticketConfirmation: true,
    ticketDecision: true,

    twoFactor: false,
  };

  tabs = [
    { id: 'general', label: 'General', icon: '⚙' },
    { id: 'ai', label: 'AI Agent', icon: '✦' },
    { id: 'support', label: 'Support', icon: '◉' },
    { id: 'delivery', label: 'Delivery', icon: '⌖' },
    { id: 'email', label: 'Email', icon: '✉' },
    { id: 'security', label: 'Security', icon: '⌑' },
  ] as const;

  setTab(tab: SettingsTab) {
    this.activeTab = tab;
    this.saved = false;
  }

  saveSettings() {
    // Connect this method to your backend API later.
    console.log('Settings:', this.settings);
    this.saved = true;
  }
}
