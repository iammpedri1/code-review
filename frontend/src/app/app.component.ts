import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';
import { ReviewService } from './review.service';
import { ReviewFinding, ReviewResponse } from './review.model';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent {
  private readonly reviewService = inject(ReviewService);

  code = `function getUser(userId) {
  const query = "SELECT * FROM users WHERE id = " + userId;
  console.log("loading user");
  return db.query(query);
}`;
  language = 'javascript';
  useAi = false;
  loading = false;
  error = '';
  result: ReviewResponse | null = null;

  get findings(): ReviewFinding[] {
    return this.result?.findings ?? [];
  }

  get lineNumbers(): string {
    return this.code.split('\n').map((_, index) => index + 1).join('\n');
  }

  analyze(): void {
    if (!this.code.trim()) {
      this.error = 'Cole algum código antes de iniciar a revisão.';
      this.result = null;
      return;
    }
    this.loading = true;
    this.error = '';
    this.result = null;
    this.reviewService.review({
      code: this.code,
      language: this.language,
      useAi: this.useAi
    })
      .pipe(finalize(() => this.loading = false))
      .subscribe({
        next: response => this.result = response,
        error: (response: HttpErrorResponse) => {
          const detail = response.error?.detail;
          this.error = typeof detail === 'string'
            ? detail
            : 'Não foi possível analisar o código. Verifique se as APIs estão em execução.';
        }
      });
  }

  severityLabel(severity: ReviewFinding['severity']): string {
    return {
      critical: 'Crítico',
      high: 'Alto',
      medium: 'Médio',
      low: 'Baixo',
      info: 'Info'
    }[severity];
  }

  providerLabel(provider: ReviewResponse['provider']): string {
    return {
      local: 'Análise local',
      openrouter: 'OpenRouter'
    }[provider];
  }
}
