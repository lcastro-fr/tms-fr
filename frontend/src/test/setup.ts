import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// El auto-cleanup de Testing Library se registra sólo si `afterEach` es global, y el
// vite.config no prende `globals`: sin esto, dos render() en un mismo archivo dejan los dos
// árboles montados y cualquier query encuentra elementos duplicados.
afterEach(cleanup);

// Mantine consulta matchMedia y ResizeObserver, que jsdom no implementa.
Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
    })),
});

class ResizeObserverMock {
    observe() {}
    unobserve() {}
    disconnect() {}
}

window.ResizeObserver = ResizeObserverMock as unknown as typeof ResizeObserver;
