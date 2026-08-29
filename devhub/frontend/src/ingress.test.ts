import {describe, expect, it} from 'vitest';
import {resolveDevHubPath} from './ingress';

describe('resolveDevHubPath', () => {
  it('preserves root API paths outside Home Assistant ingress', () => {
    expect(resolveDevHubPath('/api/projects', '/')).toBe('/api/projects');
    expect(resolveDevHubPath('/api/projects/1/roadmap', '/projects')).toBe('/api/projects/1/roadmap');
  });

  it('prefixes API requests with the Home Assistant ingress path', () => {
    const pathname = '/api/hassio_ingress/abc123/';
    expect(resolveDevHubPath('/api/projects', pathname)).toBe('/api/hassio_ingress/abc123/api/projects');
    expect(resolveDevHubPath('/api/projects/from-url', pathname)).toBe('/api/hassio_ingress/abc123/api/projects/from-url');
  });

  it('preserves an outer proxy prefix before the Home Assistant ingress path', () => {
    const pathname = '/home/api/hassio_ingress/abc123/projects';
    expect(resolveDevHubPath('/api/register', pathname)).toBe('/home/api/hassio_ingress/abc123/api/register');
  });

  it('does not rewrite non-API paths', () => {
    expect(resolveDevHubPath('https://github.com/stunwill/fynvo-home-assistant', '/api/hassio_ingress/abc123/')).toBe('https://github.com/stunwill/fynvo-home-assistant');
    expect(resolveDevHubPath('./assets/app.js', '/api/hassio_ingress/abc123/')).toBe('./assets/app.js');
  });
});
