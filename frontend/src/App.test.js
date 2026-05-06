import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from './App';

test('renders Mentoria title', () => {
  render(
    <MemoryRouter>
      <App />
    </MemoryRouter>
  );
  const titleElement = screen.getByText(/Mentoria/i);
  expect(titleElement).toBeInTheDocument();
});
