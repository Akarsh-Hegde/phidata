import React from "react";
import { render } from "@testing-library/react";
import Home from "./Home";

// Mocking next/image as it requires specific handling in test environments
jest.mock("next/image", () => ({
  __esModule: true,
  default: ({ src, alt }) => <img src={src} alt={alt} />
}));

// Mocking useDynamicYield hook,
// assuming it returns a function - adapt according to your logic
jest.mock("../hooks/useDynamicYield", () => {
  return {
    __esModule: true,
    default: jest.fn()
  };
});

describe("Home Component", () => {
  it("should render the component correctly", () => {
    const { getByAltText } = render(<Home />);
    const imageElement = getByAltText("Welcome");
    expect(imageElement).toBeInTheDocument();
  });

  it("should initialize DY object on window", () => {
    render(<Home />);
    expect(window.DY).toBeDefined();
    expect(window.DY.recommendationContext).toEqual({
      type: "HOMEPAGE",
      lng: "en_US"
    });
  });

  it("should initialize PushEngage on window", () => {
    render(<Home />);
    expect(window.PushEngage).toBeDefined();
    expect(window._peq).toBeDefined();
    expect(window.PushEngage.includes([
      "init",
      { appId: "76738e7e-07fd-4904-b4ce-01cfc4a65f4b" }
    ])).toBeTruthy();
  });

  // Add a failure case, for instance, when the image doesn't load or the hook fails
  it("should not crash if useDynamicYield throws", () => {
    const useDynamicYield = require("../hooks/useDynamicYield").default;
    useDynamicYield.mockImplementationOnce(() => {
      throw new Error("Hook failed");
    });
    expect(() => render(<Home />)).not.toThrow();
  });
});