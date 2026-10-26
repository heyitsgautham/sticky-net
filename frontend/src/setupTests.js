// Runs before every Jest test file: adds DOM matchers such as toBeInTheDocument.
import "@testing-library/jest-dom";

// jsdom has no layout, so the chat's auto-scroll call needs a stand-in.
Element.prototype.scrollIntoView = jest.fn();

// react-router 7 needs TextEncoder, which CRA's jsdom does not provide.
const { TextDecoder, TextEncoder } = require("util");
Object.assign(global, { TextDecoder, TextEncoder });
