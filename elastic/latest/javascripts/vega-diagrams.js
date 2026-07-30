(() => {
  "use strict";

  const scriptUrl = document.currentScript?.src || document.baseURI;
  const docsRoot = new URL("../", scriptUrl);

  function resolveAssets(value) {
    if (typeof value === "string" && value.startsWith("asset:")) {
      return new URL(`_media/${value.slice(6)}`, docsRoot).href;
    }
    if (Array.isArray(value)) {
      return value.map(resolveAssets);
    }
    if (value && typeof value === "object") {
      for (const key of Object.keys(value)) {
        value[key] = resolveAssets(value[key]);
      }
    }
    return value;
  }

  async function renderDiagram(code) {
    if (code.dataset.vegaRendered === "true") {
      return;
    }
    code.dataset.vegaRendered = "true";

    const source = code.closest(".highlight") || code.closest("pre");
    try {
      const spec = resolveAssets(JSON.parse(code.textContent));
      const figure = document.createElement("figure");
      figure.className = "vega-architecture-diagram";

      const viewContainer = document.createElement("div");
      viewContainer.className = "vega-architecture-diagram__view";
      viewContainer.setAttribute("role", "img");
      viewContainer.setAttribute(
        "aria-label",
        spec.description || "Architecture diagram",
      );
      figure.appendChild(viewContainer);
      source.before(figure);

      const runtime = window.vega.parse(spec);
      const view = new window.vega.View(runtime, {
        container: viewContainer,
        renderer: "svg",
        hover: false,
      });
      await view.runAsync();

      const svg = viewContainer.querySelector("svg");
      if (svg) {
        svg.setAttribute("role", "presentation");
        svg.setAttribute("focusable", "false");
        svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
      }
      source.remove();
    } catch (error) {
      code.dataset.vegaRendered = "false";
      const message = document.createElement("p");
      message.className = "vega-architecture-diagram__error";
      message.textContent = "The interactive architecture diagram could not be rendered.";
      source.before(message);
      console.error("Unable to render Vega architecture diagram", error);
    }
  }

  function renderAll() {
    if (!window.vega) {
      return;
    }
    document
      .querySelectorAll("code.language-vega, .vega code")
      .forEach((code) => renderDiagram(code));
  }

  if (typeof document$ !== "undefined") {
    document$.subscribe(renderAll);
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", renderAll, {once: true});
  } else {
    renderAll();
  }
})();
