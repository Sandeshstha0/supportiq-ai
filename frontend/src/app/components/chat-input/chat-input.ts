
import { Component, output, signal, input } from '@angular/core';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-chat-input',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './chat-input.html',
  styleUrl: './chat-input.scss'
})
export class ChatInput {

  message = signal('');

  messageSent = output<string>();

  // Loading state received from parent
  loading = input(false);

  // Input expansion state
  isExpanded = signal(false);

  expandInput(): void {
    this.isExpanded.set(true);
  }

  collapseInput(): void {
    if (!this.message().trim()) {
      this.isExpanded.set(false);
    }
  }

  sendMessage(): void {
    const text = this.message().trim();

    if (!text || this.loading()) {
      return;
    }

    this.messageSent.emit(text);
    this.message.set('');
    this.isExpanded.set(false);
  }

  handleKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }
}
