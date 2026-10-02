import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ReviewRequest, ReviewResponse } from './review.model';

@Injectable({ providedIn: 'root' })
export class ReviewService {
  private readonly http = inject(HttpClient);

  review(request: ReviewRequest): Observable<ReviewResponse> {
    return this.http.post<ReviewResponse>('/api/reviews', request);
  }
}
