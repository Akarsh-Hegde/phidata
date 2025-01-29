import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';

import GlobalError from './GlobalError';

describe('GlobalError Component', () => {
  const mockError = new Error('Test Error');
  mockError.digest = 'test-digest';
  const mockReset = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders error message', () => {
    render(<GlobalError error={mockError} reset={mockReset} />);
    expect(screen.getByText("Oops!")).toBeInTheDocument();
    expect(screen.getByText("It seems something went wrong. We're working to fix it.")).toBeInTheDocument();
  });

  test('renders Try Again button and calls reset on click', () => {
    render(<GlobalError error={mockError} reset={mockReset} />);
    const tryAgainButton = screen.getByText("Try Again");
    expect(tryAgainButton).toBeInTheDocument();
    userEvent.click(tryAgainButton);
    expect(mockReset).toHaveBeenCalled();
  });

  test('fetch is called when not on localhost', () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        json: () => Promise.resolve({}),
      })
    );

    const originalLocation = window.location;
    delete window.location;
    // Mocking for production environment
    window.location = { ...originalLocation, hostname: 'example.com' };

    render(<GlobalError error={mockError} reset={mockReset} />);
    
    expect(global.fetch).toHaveBeenCalledTimes(1);
    expect(global.fetch).toHaveBeenCalledWith(
      "https://flow.4gd.ai/prod/v1/cdb237af-e1fb-46b3-8b3c-a99e2ee06af1",
      expect.any(Object)
    );

    // Restore window.location
    window.location = originalLocation;
  });

  test('no fetch call on localhost', () => {
    global.fetch = jest.fn();

    const originalLocation = window.location;
    delete window.location;
    // Mocking for localhost environment
    window.location = { ...originalLocation, hostname: 'localhost' };

    render(<GlobalError error={mockError} reset={mockReset} />);
    
    expect(global.fetch).not.toHaveBeenCalled();

    // Restore window.location
    window.location = originalLocation;
  });

  test('console.log is called for error details', () => {
    const consoleSpy = jest.spyOn(console, 'log');
    render(<GlobalError error={mockError} reset={mockReset} />);
    expect(consoleSpy).toHaveBeenCalledWith(
      expect.stringContaining("Detailed Error Log:"),
      expect.any(Object)
    );
  });
});