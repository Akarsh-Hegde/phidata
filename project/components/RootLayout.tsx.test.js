import React from 'react';
import { render, screen } from '@testing-library/react';
import RootLayout from './RootLayout';

describe('RootLayout Component', () => {
  test('it renders without crashing', () => {
    render(<RootLayout />);
    expect(screen.getByTestId('root-layout')).toBeInTheDocument();
  });

  // More test cases here
});