import { Component } from '@angular/core';

import { Sidebar } from './components/sidebar/sidebar';
import { ChatHeader } from './components/chat-header/chat-header';
import { WelcomeScreen } from './components/welcome-screen/welcome-screen';
import { ChatInput } from './components/chat-input/chat-input';
import { ChatMessage } from './components/chat-message/chat-message';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    Sidebar,
    ChatHeader,
    WelcomeScreen,
    ChatInput,
    // ChatMessage
  ],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {}