import {
  Component,
  signal,
  inject,
  AfterViewChecked,
  ElementRef,
  ViewChild,
  OnInit,
  PLATFORM_ID
} from '@angular/core';

import { isPlatformBrowser } from '@angular/common';

import { Sidebar } from './components/sidebar/sidebar';
import { ChatHeader } from './components/chat-header/chat-header';
import { WelcomeScreen } from './components/welcome-screen/welcome-screen';
import { ChatInput } from './components/chat-input/chat-input';
import { ChatMessage } from './components/chat-message/chat-message';

import { ChatService } from './services/chat.service';

interface ChatMessageData {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    Sidebar,
    ChatHeader,
    WelcomeScreen,
    ChatInput,
    ChatMessage
  ],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App implements OnInit, AfterViewChecked {
  private chatService = inject(ChatService);
  private platformId = inject(PLATFORM_ID);

  @ViewChild('chatScroll')
  private chatScroll!: ElementRef<HTMLElement>;

  private lastMessageCount = -1;

  private readonly storageKey = 'supportiq_guest_session';

  guestSessionToken = signal<string | null>(null);
  isInitializingSession = signal(true);

  messages = signal<ChatMessageData[]>([]);
  conversationId = signal<number | null>(null);
  conversations = signal<any[]>([]);

  isLoading = signal(false);
  isLoadingHistory = signal(false);
  errorMessage = signal('');

  ngOnInit(): void {
    this.initializeGuestSession();
  }

  // Create a guest session or restore the existing one.
 private initializeGuestSession(): void {
  // Prevent localStorage access during server-side rendering.
  if (!isPlatformBrowser(this.platformId)) {
    return;
  }

  const savedToken = localStorage.getItem(this.storageKey);

  this.chatService.createOrGetGuestSession(
    savedToken || undefined
  ).subscribe({
    next: (response) => {
      localStorage.setItem(
        this.storageKey,
        response.session_token
      );

      this.guestSessionToken.set(response.session_token);
      this.isInitializingSession.set(false);

      this.loadConversations();
    },
    error: (error) => {
      console.error('Guest session initialization failed:', error);

      this.errorMessage.set(
        'Could not initialize your support session. Please refresh and try again.'
      );

      this.isInitializingSession.set(false);
    }
  });
}

  ngAfterViewChecked(): void {
    const currentCount = this.messages().length;

    if (currentCount !== this.lastMessageCount) {
      this.lastMessageCount = currentCount;
      this.scrollToBottom();
    }
  }

  private scrollToBottom(): void {
    if (!this.chatScroll) return;

    const element = this.chatScroll.nativeElement;

    if (typeof element.scrollTo === 'function') {
      element.scrollTo({
        top: element.scrollHeight,
        behavior: 'smooth'
      });
    } else {
      element.scrollTop = element.scrollHeight;
    }
  }

  // Load conversations belonging to this guest session.
  loadConversations(): void {
    const token = this.guestSessionToken();

    if (!token) return;

    this.chatService.getConversations(token).subscribe({
      next: (response) => {
        this.conversations.set(response.conversations);
      },
      error: (error) => {
        console.error('Could not load conversations:', error);
      }
    });
  }

  // Open an existing conversation.
  openConversation(conversationId: number): void {
    const token = this.guestSessionToken();

    if (!token || this.isLoading() || this.isLoadingHistory()) return;

    this.isLoadingHistory.set(true);
    this.errorMessage.set('');

    this.chatService.getConversationMessages(
      conversationId,
      token
    ).subscribe({
      next: (response) => {
        this.conversationId.set(response.conversation_id);

        this.messages.set(
          response.messages.map(message => ({
            role: message.role,
            content: message.content,
            timestamp: new Date()
          }))
        );

        this.isLoadingHistory.set(false);
      },
      error: (error) => {
        console.error('Could not open conversation:', error);
        this.errorMessage.set(
          'Could not load this conversation. Please try again.'
        );
        this.isLoadingHistory.set(false);
      }
    });
  }

  // Start a fresh conversation.
  newChat(): void {
    this.messages.set([]);
    this.conversationId.set(null);
    this.errorMessage.set('');
    this.isLoading.set(false);
    this.isLoadingHistory.set(false);
  }

  // Send a message to SupportIQ AI.
  sendMessage(message: string): void {
    const text = message.trim();
    const token = this.guestSessionToken();

    if (
      !text ||
      !token ||
      this.isLoading() ||
      this.isLoadingHistory() ||
      this.isInitializingSession()
    ) return;

    this.messages.update(current => [
      ...current,
      {
        role: 'user',
        content: text,
        timestamp: new Date()
      }
    ]);

    this.isLoading.set(true);
    this.errorMessage.set('');

    const request = {
      message: text,
      session_token: token,
      ...(this.conversationId()
        ? { conversation_id: this.conversationId()! }
        : {})
    };

    this.chatService.sendMessage(request).subscribe({
      next: (response) => {
        this.conversationId.set(response.conversation_id);

        this.messages.update(current => [
          ...current,
          {
            role: 'assistant',
            content: response.reply,
            timestamp: new Date()
          }
        ]);

        this.isLoading.set(false);
        this.loadConversations();
      },

      error: (error) => {
        console.error('Chat API error:', error);

        this.errorMessage.set(
          'Sorry, I could not connect to SupportIQ AI. Please try again.'
        );

        this.isLoading.set(false);
      }
    });
  }

  // Delete a conversation belonging to this guest.
  deleteConversation(conversationId: number): void {
    const token = this.guestSessionToken();

    if (!token) return;

    this.chatService.deleteConversation(
      conversationId,
      token
    ).subscribe({
      next: () => {
        this.conversations.update(current =>
          current.filter(
            conversation =>
              conversation.conversation_id !== conversationId
          )
        );

        if (this.conversationId() === conversationId) {
          this.newChat();
        }
      },
      error: (error) => {
        console.error('Could not delete conversation:', error);
        this.errorMessage.set(
          'Could not delete this conversation. Please try again.'
        );
      }
    });
  }

  confirmDeleteConversation(conversationId: number): void {
  const confirmed = window.confirm(
    'Are you sure you want to delete this conversation? This action cannot be undone.'
  );

  if (!confirmed) return;

  this.deleteConversation(conversationId);
}
}
