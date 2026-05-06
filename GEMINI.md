# Mentoria - Project Overview

Mentoria is an AI-powered interactive interview preparation platform designed to help candidates practice mock interviews with real-time multimodal feedback. The platform analyzes audio, video, and text to provide comprehensive evaluations, including emotion detection, speech metrics, and technical accuracy.

## Architecture

The project follows a full-stack architecture with a clear separation between the frontend and backend.

### Backend (FastAPI)
- **Framework:** FastAPI (Python 3.9+)
- **Routing:** Organized into domain-specific routers (resume, questions, evaluation).
- **Services:** Stateless business logic for AI integrations, analytics, and session management.
- **State Management:** In-memory interview sessions for active interviews, persistent JSON storage for analytics and peer reviews.
- **AI Stack:**
  - **LLM:** Google Gemini (primary) and Ollama (fallback for question generation).
  - **Speech-to-Text:** OpenAI Whisper.
  - **Computer Vision:** MediaPipe (face/pose landmarks) and DeepFace (emotion classification).
  - **Audio Analysis:** Librosa for tone and speech metrics.

### Frontend (React)
- **Framework:** React 18.2 with React Router 6.
- **Authentication:** Firebase Auth (Email/Password & Google OAuth).
- **Database:** Firebase Firestore for user profiles and adaptive learning data.
- **Real-time Monitoring:** Captures camera frames and audio blobs for backend analysis during the interview.

## Building and Running

### Prerequisites
- Python 3.9+
- Node.js & npm
- (Optional) Ollama running locally for local LLM support.

### Backend Setup
1. Navigate to the `backend` directory.
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   source venv/bin/activate # Unix/macOS
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file based on the project structure (requires `GEMINI_API_KEY`).
5. Run the server:
   ```bash
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Frontend Setup
1. Navigate to the `frontend` directory.
2. Install dependencies:
   ```bash
   npm install
   ```
3. Create a `.env` file with Firebase credentials and `REACT_APP_API_BASE=http://localhost:8000`.
4. Start the development server:
   ```bash
   npm start
   ```

## Development Conventions

### Backend
- **Async First:** Use `async def` for route handlers and service methods that involve I/O or AI calls.
- **Pydantic Models:** Always use Pydantic models for request validation and response serialization (located in `app/models`).
- **Service Pattern:** Business logic should reside in `app/services`, keeping routers thin.
- **Error Handling:** Use `HTTPException` for API errors and provide descriptive detail.
- **AI Routing:** The `llm_router` service manages fallback logic between Ollama and Gemini.

### Frontend
- **API Client:** All backend communication should go through `frontend/src/api.js`.
- **State Management:** Use React hooks (`useState`, `useEffect`) for local state and Firebase for global user/profile state.
- **Modular Styles:** CSS files are paired with their respective components/pages.

### Testing
- **Backend:** Testing can be performed using `pytest`. (TODO: Add explicit test suite)
- **Frontend:** Uses React Testing Library and Jest (`npm test`).

## Key Files
- `backend/app/main.py`: Entry point for the FastAPI application.
- `backend/app/interview_engine.py`: Manages the state and flow of interview sessions.
- `backend/app/services/llm_router.py`: Handles AI model selection and fallbacks.
- `frontend/src/api.js`: Centralized API communication layer.
- `frontend/src/pages/Interview.jsx`: Core component for the live interview experience.
