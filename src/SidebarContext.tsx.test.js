import React, { useContext } from 'react';
import { render } from '@testing-library/react';
import '@testing-library/jest-dom/extend-expect';
import { SidebarContext } from '../../src/context/SidebarContext';

describe('SidebarContext', () => {
  it('should have default values', () => {
    const ConsumerComponent = () => {
      const { isExpanded, toggleSidebar } = useContext(SidebarContext);
      // This can be expanded depending on what functionalities toggleSidebar might perform
      return (
        <div>
          <span>{`Is Expanded: ${isExpanded}`}</span>
          <button onClick={() => toggleSidebar()}>Toggle</button>
        </div>
      );
    };

    const { getByText } = render(<ConsumerComponent />);

    expect(getByText(/Is Expanded: false/i)).toBeInTheDocument();
  });

  it('should call toggleSidebar function', () => {
    let sidebarState = {
      isExpanded: false,
      toggleSidebar: jest.fn(),
    };

    const ConsumerComponent = () => {
      const { isExpanded, toggleSidebar } = sidebarState;
      return (
        <div>
          <span>{`Is Expanded: ${isExpanded}`}</span>
          <button onClick={() => toggleSidebar()}>Toggle</button>
        </div>
      );
    };

    const { getByText } = render(<ConsumerComponent />);
    const button = getByText('Toggle');
    button.click();

    expect(sidebarState.toggleSidebar).toHaveBeenCalled();
  });
});