
import { Component, output } from '@angular/core';

@Component({
  selector: 'app-welcome-screen',
  standalone: true,
  imports: [],
  templateUrl: './welcome-screen.html',
  styleUrl: './welcome-screen.scss'
})
export class WelcomeScreen {

  promptSelected = output<string>();

  suggestions = [
    {
      icon: '🛒',
      title: 'Explore Products',
      description: 'Find groceries and everyday essentials.',
      prompt: 'What products are available at Lasata?',
      color: 'sky'
    },
    {
      icon: '🚚',
      title: 'Delivery Information',
      description: 'Learn about delivery services and locations.',
      prompt: 'Tell me about Lasata delivery services.',
      color: 'yellow'
    },
    {
      icon: '↩',
      title: 'Returns & Refunds',
      description: 'Get help with returns and refund policies.',
      prompt: 'What is the return and refund policy?',
      color: 'sky'
    },
    {
      icon: '🎧',
      title: 'Customer Support',
      description: 'Get assistance with your questions.',
      prompt: 'I need help from customer support.',
      color: 'yellow'
    }
  ];

  selectPrompt(prompt: string): void {
    this.promptSelected.emit(prompt);
  }

}
