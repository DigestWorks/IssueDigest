import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

// jsdom lacks the browser modal methods; native cancellation is dispatched in dialog tests.
Object.defineProperty(HTMLDialogElement.prototype, 'showModal', {configurable:true, value:function(this:HTMLDialogElement) {this.open=true;}});
Object.defineProperty(HTMLDialogElement.prototype, 'close', {configurable:true, value:function(this:HTMLDialogElement) {this.open=false;}});
