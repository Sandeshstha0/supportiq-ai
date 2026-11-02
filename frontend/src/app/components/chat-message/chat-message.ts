
import { Component, Input } from '@angular/core';
import { DatePipe } from '@angular/common';
import { MarkdownComponent } from 'ngx-markdown';

@Component({
  selector: 'app-chat-message',
  standalone: true,
  imports: [
    DatePipe,
    MarkdownComponent
  ],
  templateUrl: './chat-message.html',
  styleUrl: './chat-message.scss'
})
export class ChatMessage {
  @Input() role: 'user' | 'assistant' = 'assistant';
  @Input() content = '';
  @Input() timestamp: Date | string = new Date();

  get isUser(): boolean {
    return this.role === 'user';
  }
}
