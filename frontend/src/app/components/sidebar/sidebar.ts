
import { Component, signal, output, input } from '@angular/core';

interface ConversationItem {
  conversation_id: number;
  title: string;
  last_message: string;
}

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [],
  templateUrl: './sidebar.html',
  styleUrl: './sidebar.scss'
})
export class Sidebar {
  collapsed = signal(false);

  conversations = input<ConversationItem[]>([]);
  activeConversationId = input<number | null>(null);

  newChatClicked = output<void>();
  conversationSelected = output<number>();
  conversationDeleteRequested = output<number>();

  toggleSidebar(): void {
    this.collapsed.update(value => !value);
  }

  startNewChat(): void {
    this.newChatClicked.emit();
  }

  openConversation(id: number): void {
    this.conversationSelected.emit(id);
  }

  requestDelete(id: number, event: MouseEvent): void {
    event.stopPropagation();
    this.conversationDeleteRequested.emit(id);
  }
}
