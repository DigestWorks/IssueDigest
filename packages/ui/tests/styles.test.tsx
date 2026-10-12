/// <reference types="node" />
import { readFileSync } from 'node:fs';
import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { CanvasView } from '../src';

const stylesheet = readFileSync('packages/ui/src/styles.css', 'utf8');
const hostStyles = `
  .host-example { display: block; padding-top: 7px; margin-bottom: 5px; font-size: 18px; }
  .host-edge { transform: none; }
`;

function computed(element: Element) {
  return element.ownerDocument.defaultView!.getComputedStyle(element);
}

describe('canvas stylesheet containment', () => {
  it('preserves outside host layout while applying the canvas state style inside its container', () => {
    const { container } = render(<>
      <style>{hostStyles + stylesheet}</style>
      <div className="host-example id-canvas-header">Host header</div>
      <div className="host-example id-canvas-grid">Host grid</div>
      <div className="host-example id-canvas-state">Host state</div>
      <CanvasView bundle={null} />
    </>);
    const outside = container.querySelectorAll('.host-example');
    expect(computed(outside[0]).display).toBe('block');
    expect(computed(outside[0]).marginBottom).toBe('5px');
    expect(computed(outside[1]).display).toBe('block');
    expect(computed(outside[2]).paddingTop).toBe('7px');
    expect(computed(container.querySelector('.id-canvas .id-canvas-state')!).paddingTop).toBe('32px');
  });

  it('contains both sides of a comma-separated selector and retains outside host typography', () => {
    const { container } = render(<>
      <style>{hostStyles + stylesheet}</style>
      <div className="id-canvas-header"><p className="host-example">Host paragraph</p></div>
      <p className="host-example id-canvas-note">Host note</p>
      <div className="id-canvas"><p className="id-canvas-note">Canvas note</p></div>
    </>);
    container.querySelectorAll('.host-example').forEach(element => {
      expect(computed(element).fontSize).toBe('18px');
    });
    expect(computed(container.querySelector('.id-canvas .id-canvas-note')!).fontSize).toBe('14.4px');
  });

  it('contains active narrow-screen rules while retaining responsive styles inside the canvas', () => {
    const { container } = render(<>
      <style>{hostStyles + stylesheet}</style>
      <div className="host-example id-canvas-module">Host module</div>
      <div className="id-canvas-edge"><span className="host-edge">Host edge</span></div>
      <div className="id-canvas"><div className="id-canvas-module">Canvas module</div><div className="id-canvas-edge"><span>Canvas edge</span></div></div>
    </>);
    // jsdom does not evaluate viewport media queries. Activate the real parsed media
    // declarations to exercise their cascade; the controller checks actual browser widths.
    const rules = container.querySelector('style')!.sheet!.cssRules;
    const activeMedia = container.ownerDocument.createElement('style');
    activeMedia.textContent = [...rules].filter(rule => rule.type === 4)
      .flatMap(rule => [...(rule as CSSMediaRule).cssRules].map(child => child.cssText)).join('\n');
    container.append(activeMedia);
    expect(computed(container.querySelector('.host-example')!).paddingTop).toBe('7px');
    expect(computed(container.querySelector('.host-edge')!).transform).toBe('none');
    expect(computed(container.querySelector('.id-canvas .id-canvas-module')!).paddingTop).toBe('16px');
    expect(computed(container.querySelector('.id-canvas .id-canvas-edge span')!).transform).toBe('rotate(90deg)');
  });
});
