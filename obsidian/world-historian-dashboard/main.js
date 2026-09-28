"use strict";
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key2 of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key2) && key2 !== except)
        __defProp(to, key2, { get: () => from[key2], enumerable: !(desc = __getOwnPropDesc(from, key2)) || desc.enumerable });
  }
  return to;
};
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// src/main.ts
var main_exports = {};
__export(main_exports, {
  default: () => HistorianPlugin
});
module.exports = __toCommonJS(main_exports);
var import_obsidian = require("obsidian");
var import_node_child_process = require("node:child_process");
var import_node_fs2 = require("node:fs");

// node_modules/esm-env/dev-fallback.js
var node_env = globalThis.process?.env?.NODE_ENV;
var dev_fallback_default = node_env && !node_env.toLowerCase().startsWith("prod");

// node_modules/svelte/src/internal/shared/utils.js
var is_array = Array.isArray;
var index_of = Array.prototype.indexOf;
var includes = Array.prototype.includes;
var array_from = Array.from;
var object_keys = Object.keys;
var define_property = Object.defineProperty;
var get_descriptor = Object.getOwnPropertyDescriptor;
var get_descriptors = Object.getOwnPropertyDescriptors;
var object_prototype = Object.prototype;
var array_prototype = Array.prototype;
var get_prototype_of = Object.getPrototypeOf;
var is_extensible = Object.isExtensible;
var noop = () => {
};
function run(fn) {
  return fn();
}
function run_all(arr) {
  for (var i = 0; i < arr.length; i++) {
    arr[i]();
  }
}
function deferred() {
  var resolve;
  var reject;
  var promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}
function to_array(value, n) {
  if (Array.isArray(value)) {
    return value;
  }
  if (n === void 0 || !(Symbol.iterator in value)) {
    return Array.from(value);
  }
  const array = [];
  for (const element2 of value) {
    array.push(element2);
    if (array.length === n) break;
  }
  return array;
}

// node_modules/svelte/src/internal/client/constants.js
var DERIVED = 1 << 1;
var EFFECT = 1 << 2;
var RENDER_EFFECT = 1 << 3;
var MANAGED_EFFECT = 1 << 24;
var BLOCK_EFFECT = 1 << 4;
var BRANCH_EFFECT = 1 << 5;
var ROOT_EFFECT = 1 << 6;
var BOUNDARY_EFFECT = 1 << 7;
var PAUSED = 1 << 8;
var CONNECTED = 1 << 9;
var CLEAN = 1 << 10;
var DIRTY = 1 << 11;
var MAYBE_DIRTY = 1 << 12;
var INERT = 1 << 13;
var DESTROYED = 1 << 14;
var REACTION_RAN = 1 << 15;
var DESTROYING = 1 << 25;
var EFFECT_TRANSPARENT = 1 << 16;
var EAGER_EFFECT = 1 << 17;
var HEAD_EFFECT = 1 << 18;
var EFFECT_PRESERVED = 1 << 19;
var USER_EFFECT = 1 << 20;
var EFFECT_OFFSCREEN = 1 << 25;
var REACTION_IS_UPDATING = 1 << 21;
var ASYNC = 1 << 22;
var ERROR_VALUE = 1 << 23;
var STATE_SYMBOL = Symbol("$state");
var COMPONENT_SYMBOL = Symbol("component");
var LEGACY_PROPS = Symbol("legacy props");
var LOADING_ATTR_SYMBOL = Symbol("");
var PROXY_PATH_SYMBOL = Symbol("proxy path");
var ATTRIBUTES_CACHE = Symbol("attributes");
var CLASS_CACHE = Symbol("class");
var STYLE_CACHE = Symbol("style");
var TEXT_CACHE = Symbol("text");
var FORM_RESET_HANDLER = Symbol("form reset");
var HMR_ANCHOR = Symbol("hmr anchor");
var STALE_REACTION = new class StaleReactionError extends Error {
  name = "StaleReactionError";
  message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}();
var IS_XHTML = (
  // We gotta write it like this because after downleveling the pure comment may end up in the wrong location
  !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml")
);
var TEXT_NODE = 3;
var COMMENT_NODE = 8;

// node_modules/svelte/src/constants.js
var EACH_ITEM_REACTIVE = 1;
var EACH_INDEX_REACTIVE = 1 << 1;
var EACH_IS_CONTROLLED = 1 << 2;
var EACH_IS_ANIMATED = 1 << 3;
var EACH_ITEM_IMMUTABLE = 1 << 4;
var PROPS_IS_IMMUTABLE = 1;
var PROPS_IS_RUNES = 1 << 1;
var PROPS_IS_UPDATED = 1 << 2;
var PROPS_IS_BINDABLE = 1 << 3;
var PROPS_IS_LAZY_INITIAL = 1 << 4;
var TRANSITION_OUT = 1 << 1;
var TRANSITION_GLOBAL = 1 << 2;
var TEMPLATE_FRAGMENT = 1;
var TEMPLATE_USE_IMPORT_NODE = 1 << 1;
var TEMPLATE_USE_SVG = 1 << 2;
var TEMPLATE_USE_MATHML = 1 << 3;
var HYDRATION_START = "[";
var HYDRATION_START_ELSE = "[!";
var HYDRATION_START_FAILED = "[?";
var HYDRATION_END = "]";
var HYDRATION_ERROR = {};
var ELEMENT_PRESERVE_ATTRIBUTE_CASE = 1 << 1;
var ELEMENT_IS_INPUT = 1 << 2;
var UNINITIALIZED = Symbol("uninitialized");
var FILENAME = Symbol("filename");
var HMR = Symbol("hmr");
var NAMESPACE_HTML = "http://www.w3.org/1999/xhtml";

// node_modules/svelte/src/internal/client/warnings.js
var bold = "font-weight: bold";
var normal = "font-weight: normal";
function await_reactivity_loss(name) {
  if (dev_fallback_default) {
    console.warn(`%c[svelte] await_reactivity_loss
%cDetected reactivity loss when reading \`${name}\`. This happens when state is read in an async function after an earlier \`await\`
https://svelte.dev/e/await_reactivity_loss`, bold, normal);
  } else {
    console.warn(`https://svelte.dev/e/await_reactivity_loss`);
  }
}
function await_waterfall(name, location) {
  if (dev_fallback_default) {
    console.warn(`%c[svelte] await_waterfall
%cAn async derived, \`${name}\` (${location}) was not read immediately after it resolved. This often indicates an unnecessary waterfall, which can slow down your app
https://svelte.dev/e/await_waterfall`, bold, normal);
  } else {
    console.warn(`https://svelte.dev/e/await_waterfall`);
  }
}
function derived_inert() {
  if (dev_fallback_default) {
    console.warn(`%c[svelte] derived_inert
%cReading a derived belonging to a now-destroyed effect may result in stale values
https://svelte.dev/e/derived_inert`, bold, normal);
  } else {
    console.warn(`https://svelte.dev/e/derived_inert`);
  }
}
function hydration_attribute_changed(attribute, html2, value) {
  if (dev_fallback_default) {
    console.warn(`%c[svelte] hydration_attribute_changed
%cThe \`${attribute}\` attribute on \`${html2}\` changed its value between server and client renders. The client value, \`${value}\`, will be ignored in favour of the server value
https://svelte.dev/e/hydration_attribute_changed`, bold, normal);
  } else {
    console.warn(`https://svelte.dev/e/hydration_attribute_changed`);
  }
}
function hydration_mismatch(location) {
  if (dev_fallback_default) {
    console.warn(
      `%c[svelte] hydration_mismatch
%c${location ? `Hydration failed because the initial UI does not match what was rendered on the server. The error occurred near ${location}` : "Hydration failed because the initial UI does not match what was rendered on the server"}
https://svelte.dev/e/hydration_mismatch`,
      bold,
      normal
    );
  } else {
    console.warn(`https://svelte.dev/e/hydration_mismatch`);
  }
}
function lifecycle_double_unmount() {
  if (dev_fallback_default) {
    console.warn(`%c[svelte] lifecycle_double_unmount
%cTried to unmount a component that was not mounted
https://svelte.dev/e/lifecycle_double_unmount`, bold, normal);
  } else {
    console.warn(`https://svelte.dev/e/lifecycle_double_unmount`);
  }
}
function select_multiple_invalid_value() {
  if (dev_fallback_default) {
    console.warn(`%c[svelte] select_multiple_invalid_value
%cThe \`value\` property of a \`<select multiple>\` element should be an array, but it received a non-array value. The selection will be kept as is.
https://svelte.dev/e/select_multiple_invalid_value`, bold, normal);
  } else {
    console.warn(`https://svelte.dev/e/select_multiple_invalid_value`);
  }
}
function state_proxy_equality_mismatch(operator) {
  if (dev_fallback_default) {
    console.warn(`%c[svelte] state_proxy_equality_mismatch
%cReactive \`$state(...)\` proxies and the values they proxy have different identities. Because of this, comparisons with \`${operator}\` will produce unexpected results
https://svelte.dev/e/state_proxy_equality_mismatch`, bold, normal);
  } else {
    console.warn(`https://svelte.dev/e/state_proxy_equality_mismatch`);
  }
}
function svelte_boundary_reset_noop() {
  if (dev_fallback_default) {
    console.warn(`%c[svelte] svelte_boundary_reset_noop
%cA \`<svelte:boundary>\` \`reset\` function only resets the boundary the first time it is called
https://svelte.dev/e/svelte_boundary_reset_noop`, bold, normal);
  } else {
    console.warn(`https://svelte.dev/e/svelte_boundary_reset_noop`);
  }
}

// node_modules/svelte/src/internal/client/dom/hydration.js
var hydrating = false;
function set_hydrating(value) {
  hydrating = value;
}
var hydrate_node;
function set_hydrate_node(node) {
  if (node === null) {
    hydration_mismatch();
    throw HYDRATION_ERROR;
  }
  return hydrate_node = node;
}
function hydrate_next() {
  return set_hydrate_node(get_next_sibling(hydrate_node));
}
function reset(node) {
  if (!hydrating) return;
  if (get_next_sibling(hydrate_node) !== null) {
    hydration_mismatch();
    throw HYDRATION_ERROR;
  }
  hydrate_node = node;
}
function next(count = 1) {
  if (hydrating) {
    var i = count;
    var node = hydrate_node;
    while (i--) {
      node = /** @type {TemplateNode} */
      get_next_sibling(node);
    }
    hydrate_node = node;
  }
}
function skip_nodes(remove = true) {
  var depth = 0;
  var node = hydrate_node;
  while (true) {
    if (node.nodeType === COMMENT_NODE) {
      var data = (
        /** @type {Comment} */
        node.data
      );
      if (data === HYDRATION_END) {
        if (depth === 0) return node;
        depth -= 1;
      } else if (data === HYDRATION_START || data === HYDRATION_START_ELSE || // "[1", "[2", etc. for if blocks
      data[0] === "[" && !isNaN(Number(data.slice(1)))) {
        depth += 1;
      }
    }
    var next2 = (
      /** @type {TemplateNode} */
      get_next_sibling(node)
    );
    if (remove) node.remove();
    node = next2;
  }
}
function read_hydration_instruction(node) {
  if (!node || node.nodeType !== COMMENT_NODE) {
    hydration_mismatch();
    throw HYDRATION_ERROR;
  }
  return (
    /** @type {Comment} */
    node.data
  );
}

// node_modules/svelte/src/internal/client/reactivity/equality.js
function equals(value) {
  return value === this.v;
}
function safe_not_equal(a, b) {
  return a != a ? b == b : a !== b || a !== null && typeof a === "object" || typeof a === "function";
}
function safe_equals(value) {
  return !safe_not_equal(value, this.v);
}

// node_modules/svelte/src/internal/shared/errors.js
function invariant_violation(message) {
  if (dev_fallback_default) {
    const error = new Error(`invariant_violation
An invariant violation occurred, meaning Svelte's internal assumptions were flawed. This is a bug in Svelte, not your app \u2014 please open an issue at https://github.com/sveltejs/svelte, citing the following message: "${message}"
https://svelte.dev/e/invariant_violation`);
    error.name = "Svelte error";
    throw error;
  } else {
    throw new Error(`https://svelte.dev/e/invariant_violation`);
  }
}
function lifecycle_outside_component(name) {
  if (dev_fallback_default) {
    const error = new Error(`lifecycle_outside_component
\`${name}(...)\` can only be used during component initialisation
https://svelte.dev/e/lifecycle_outside_component`);
    error.name = "Svelte error";
    throw error;
  } else {
    throw new Error(`https://svelte.dev/e/lifecycle_outside_component`);
  }
}

// node_modules/svelte/src/internal/client/errors.js
function async_derived_orphan() {
  if (dev_fallback_default) {
    const error = new Error(`async_derived_orphan
Cannot create a \`$derived(...)\` with an \`await\` expression outside of an effect tree
https://svelte.dev/e/async_derived_orphan`);
    error.name = "Svelte error";
    throw error;
  } else {
    throw new Error(`https://svelte.dev/e/async_derived_orphan`);
  }
}
function bind_invalid_checkbox_value() {
  if (dev_fallback_default) {
    const error = new Error(`bind_invalid_checkbox_value
Using \`bind:value\` together with a checkbox input is not allowed. Use \`bind:checked\` instead
https://svelte.dev/e/bind_invalid_checkbox_value`);
    error.name = "Svelte error";
    throw error;
  } else {
    throw new Error(`https://svelte.dev/e/bind_invalid_checkbox_value`);
  }
}
function derived_references_self() {
  if (dev_fallback_default) {
    const error = new Error(`derived_references_self
A derived value cannot reference itself recursively
https://svelte.dev/e/derived_references_self`);
    error.name = "Svelte error";
    throw error;
  } else {
    throw new Error(`https://svelte.dev/e/derived_references_self`);
  }
}
function each_key_duplicate(a, b, value) {
  if (dev_fallback_default) {
    const error = new Error(`each_key_duplicate
${value ? `Keyed each block has duplicate key \`${value}\` at indexes ${a} and ${b}` : `Keyed each block has duplicate key at indexes ${a} and ${b}`}
https://svelte.dev/e/each_key_duplicate`);
    error.name = "Svelte error";
    throw error;
  } else {
    throw new Error(`https://svelte.dev/e/each_key_duplicate`);
  }
}
function each_key_volatile(index2, a, b) {
  if (dev_fallback_default) {
    const error = new Error(`each_key_volatile
Keyed each block has key that is not idempotent \u2014 the key for item at index ${index2} was \`${a}\` but is now \`${b}\`. Keys must be the same each time for a given item
https://svelte.dev/e/each_key_volatile`);
    error.name = "Svelte error";
    throw error;
  } else {
    throw new Error(`https://svelte.dev/e/each_key_volatile`);
  }
}
function effect_in_teardown(rune) {
  if (dev_fallback_default) {
    const error = new Error(`effect_in_teardown
\`${rune}\` cannot be used inside an effect cleanup function
https://svelte.dev/e/effect_in_teardown`);
    error.name = "Svelte error";
    throw error;
  } else {
    throw new Error(`https://svelte.dev/e/effect_in_teardown`);
  }
}
function effect_in_unowned_derived() {
  if (dev_fallback_default) {
    const error = new Error(`effect_in_unowned_derived
Effect cannot be created inside a \`$derived\` value that was not itself created inside an effect
https://svelte.dev/e/effect_in_unowned_derived`);
    error.name = "Svelte error";
    throw error;
  } else {
    throw new Error(`https://svelte.dev/e/effect_in_unowned_derived`);
  }
}
function effect_orphan(rune) {
  if (dev_fallback_default) {
    const error = new Error(`effect_orphan
\`${rune}\` can only be used inside an effect (e.g. during component initialisation)
https://svelte.dev/e/effect_orphan`);
    error.name = "Svelte error";
    throw error;
  } else {
    throw new Error(`https://svelte.dev/e/effect_orphan`);
  }
}
function effect_update_depth_exceeded() {
  if (dev_fallback_default) {
    const error = new Error(`effect_update_depth_exceeded
Maximum update depth exceeded. This typically indicates that an effect reads and writes the same piece of state
https://svelte.dev/e/effect_update_depth_exceeded`);
    error.name = "Svelte error";
    throw error;
  } else {
    throw new Error(`https://svelte.dev/e/effect_update_depth_exceeded`);
  }
}
function hydration_failed() {
  if (dev_fallback_default) {
    const error = new Error(`hydration_failed
Failed to hydrate the application
https://svelte.dev/e/hydration_failed`);
    error.name = "Svelte error";
    throw error;
  } else {
    throw new Error(`https://svelte.dev/e/hydration_failed`);
  }
}
function props_invalid_value(key2) {
  if (dev_fallback_default) {
    const error = new Error(`props_invalid_value
Cannot do \`bind:${key2}={undefined}\` when \`${key2}\` has a fallback value
https://svelte.dev/e/props_invalid_value`);
    error.name = "Svelte error";
    throw error;
  } else {
    throw new Error(`https://svelte.dev/e/props_invalid_value`);
  }
}
function rune_outside_svelte(rune) {
  if (dev_fallback_default) {
    const error = new Error(`rune_outside_svelte
The \`${rune}\` rune is only available inside \`.svelte\` and \`.svelte.js/ts\` files
https://svelte.dev/e/rune_outside_svelte`);
    error.name = "Svelte error";
    throw error;
  } else {
    throw new Error(`https://svelte.dev/e/rune_outside_svelte`);
  }
}
function state_descriptors_fixed() {
  if (dev_fallback_default) {
    const error = new Error(`state_descriptors_fixed
Property descriptors defined on \`$state\` objects must contain \`value\` and always be \`enumerable\`, \`configurable\` and \`writable\`.
https://svelte.dev/e/state_descriptors_fixed`);
    error.name = "Svelte error";
    throw error;
  } else {
    throw new Error(`https://svelte.dev/e/state_descriptors_fixed`);
  }
}
function state_prototype_fixed() {
  if (dev_fallback_default) {
    const error = new Error(`state_prototype_fixed
Cannot set prototype of \`$state\` object
https://svelte.dev/e/state_prototype_fixed`);
    error.name = "Svelte error";
    throw error;
  } else {
    throw new Error(`https://svelte.dev/e/state_prototype_fixed`);
  }
}
function state_unsafe_mutation() {
  if (dev_fallback_default) {
    const error = new Error(`state_unsafe_mutation
Updating state inside \`$derived(...)\`, \`$inspect(...)\` or a template expression is forbidden. If the value should not be reactive, declare it without \`$state\`
https://svelte.dev/e/state_unsafe_mutation`);
    error.name = "Svelte error";
    throw error;
  } else {
    throw new Error(`https://svelte.dev/e/state_unsafe_mutation`);
  }
}
function svelte_boundary_reset_onerror() {
  if (dev_fallback_default) {
    const error = new Error(`svelte_boundary_reset_onerror
A \`<svelte:boundary>\` \`reset\` function cannot be called while an error is still being handled
https://svelte.dev/e/svelte_boundary_reset_onerror`);
    error.name = "Svelte error";
    throw error;
  } else {
    throw new Error(`https://svelte.dev/e/svelte_boundary_reset_onerror`);
  }
}

// node_modules/svelte/src/internal/flags/index.js
var async_mode_flag = false;
var legacy_mode_flag = false;
var tracing_mode_flag = false;
function enable_legacy_mode_flag() {
  legacy_mode_flag = true;
}

// node_modules/svelte/src/internal/client/dev/tracing.js
var tracing_expressions = null;
function tag(source2, label) {
  source2.label = label;
  tag_proxy(source2.v, label);
  return source2;
}
function tag_proxy(value, label) {
  value?.[PROXY_PATH_SYMBOL]?.(label);
  return value;
}

// node_modules/svelte/src/internal/shared/dev.js
function get_error(label) {
  const error = new Error();
  const stack2 = get_stack();
  if (stack2.length === 0) {
    return null;
  }
  stack2.unshift("\n");
  define_property(error, "stack", {
    value: stack2.join("\n")
  });
  define_property(error, "name", {
    value: label
  });
  return (
    /** @type {Error & { stack: string }} */
    error
  );
}
function get_stack() {
  const limit = Error.stackTraceLimit;
  Error.stackTraceLimit = Infinity;
  const stack2 = new Error().stack;
  Error.stackTraceLimit = limit;
  if (!stack2) return [];
  const lines = stack2.split("\n");
  const new_lines = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const posixified = line.replaceAll("\\", "/");
    if (line.trim() === "Error") {
      continue;
    }
    if (line.includes("validate_each_keys")) {
      return [];
    }
    if (posixified.includes("svelte/src/internal") || posixified.includes("node_modules/.vite")) {
      continue;
    }
    new_lines.push(line);
  }
  return new_lines;
}
function invariant(condition, message) {
  if (!dev_fallback_default) {
    throw new Error("invariant(...) was not guarded by if (DEV)");
  }
  if (!condition) invariant_violation(message);
}

// node_modules/svelte/src/internal/client/context.js
var component_context = null;
function set_component_context(context) {
  component_context = context;
}
var dev_stack = null;
function set_dev_stack(stack2) {
  dev_stack = stack2;
}
var dev_current_component_function = null;
function set_dev_current_component_function(fn) {
  dev_current_component_function = fn;
}
function push(props, runes = false, fn) {
  component_context = {
    p: component_context,
    i: false,
    c: null,
    e: null,
    s: props,
    x: null,
    r: (
      /** @type {Effect} */
      active_effect
    ),
    l: legacy_mode_flag && !runes ? { s: null, u: null, $: [] } : null
  };
  if (dev_fallback_default) {
    component_context.function = fn;
    dev_current_component_function = fn;
  }
}
function pop(component2) {
  var context = (
    /** @type {ComponentContext} */
    component_context
  );
  var effects = context.e;
  if (effects !== null) {
    context.e = null;
    for (var fn of effects) {
      create_user_effect(fn);
    }
  }
  if (component2 !== void 0) {
    context.x = component2;
  }
  context.i = true;
  component_context = context.p;
  if (dev_fallback_default) {
    dev_current_component_function = component_context?.function ?? null;
  }
  return mark_as_component(component2);
}
function mark_as_component(component2 = {}) {
  define_property(component2, COMPONENT_SYMBOL, { value: true });
  return component2;
}
function is_runes() {
  return !legacy_mode_flag || component_context !== null && component_context.l === null;
}

// node_modules/svelte/src/internal/client/dom/task.js
var micro_tasks = [];
function run_micro_tasks() {
  var tasks = micro_tasks;
  micro_tasks = [];
  run_all(tasks);
}
function queue_micro_task(fn) {
  if (micro_tasks.length === 0 && !is_flushing_sync) {
    var tasks = micro_tasks;
    queueMicrotask(() => {
      if (tasks === micro_tasks) run_micro_tasks();
    });
  }
  micro_tasks.push(fn);
}
function flush_tasks() {
  while (micro_tasks.length > 0) {
    run_micro_tasks();
  }
}

// node_modules/svelte/src/internal/client/reactivity/status.js
var STATUS_MASK = ~(DIRTY | MAYBE_DIRTY | CLEAN);
function set_signal_status(signal, status) {
  signal.f = signal.f & STATUS_MASK | status;
}
function update_derived_status(derived2) {
  if ((derived2.f & CONNECTED) !== 0 || derived2.deps === null) {
    set_signal_status(derived2, CLEAN);
  } else {
    set_signal_status(derived2, MAYBE_DIRTY);
  }
}

// node_modules/svelte/src/internal/client/reactivity/utils.js
function defer_effect(effect2, dirty_effects, maybe_dirty_effects) {
  if ((effect2.f & DIRTY) !== 0) {
    dirty_effects.add(effect2);
  } else if ((effect2.f & MAYBE_DIRTY) !== 0) {
    maybe_dirty_effects.add(effect2);
  }
  set_signal_status(effect2, CLEAN);
}

// node_modules/svelte/src/internal/client/dom/elements/misc.js
var listening_to_form_reset = false;
function add_form_reset_listener() {
  if (!listening_to_form_reset) {
    listening_to_form_reset = true;
    document.addEventListener(
      "reset",
      (evt) => {
        Promise.resolve().then(() => {
          if (!evt.defaultPrevented) {
            for (
              const e of
              /**@type {HTMLFormElement} */
              evt.target.elements
            ) {
              e[FORM_RESET_HANDLER]?.();
            }
          }
        });
      },
      // In the capture phase to guarantee we get noticed of it (no possibility of stopPropagation)
      { capture: true }
    );
  }
}

// node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function without_reactive_context(fn) {
  var previous_reaction = active_reaction;
  var previous_effect = active_effect;
  set_active_reaction(null);
  set_active_effect(null);
  try {
    return fn();
  } finally {
    set_active_reaction(previous_reaction);
    set_active_effect(previous_effect);
  }
}
function listen_to_event_and_reset_event(element2, event2, handler, on_reset = handler) {
  element2.addEventListener(event2, () => without_reactive_context(handler));
  const prev = (
    /** @type {any} */
    element2[FORM_RESET_HANDLER]
  );
  if (prev) {
    element2[FORM_RESET_HANDLER] = () => {
      prev();
      on_reset(true);
    };
  } else {
    element2[FORM_RESET_HANDLER] = () => on_reset(true);
  }
  add_form_reset_listener();
}

// node_modules/svelte/src/internal/client/reactivity/async.js
function flatten(blockers, sync, async2, fn) {
  const d = is_runes() ? derived : derived_safe_equal;
  var pending2 = blockers.filter((b) => !b.settled);
  var deriveds = sync.map(d);
  if (dev_fallback_default) {
    deriveds.forEach((d2, i) => {
      d2.label = sync[i].toString().replace("() => ", "").replaceAll("$.eager(() => ", "$state.eager(").replace(/\$\.get\((.+?)\)/g, (_, id) => id);
    });
  }
  if (async2.length === 0 && pending2.length === 0) {
    fn(deriveds);
    return;
  }
  var parent = (
    /** @type {Effect} */
    active_effect
  );
  var restore = capture();
  var blocker_promise = pending2.length === 1 ? pending2[0].promise : pending2.length > 1 ? Promise.all(pending2.map((b) => b.promise)) : null;
  function finish(async3) {
    if ((parent.f & DESTROYED) !== 0) {
      return;
    }
    restore();
    try {
      fn([...deriveds, ...async3]);
    } catch (error) {
      invoke_error_boundary(error, parent);
    }
    unset_context();
  }
  var decrement_pending = increment_pending();
  if (async2.length === 0) {
    blocker_promise.then(() => finish([])).finally(decrement_pending);
    return;
  }
  function run3() {
    Promise.all(async2.map((expression) => async_derived(expression))).then(finish).catch((error) => invoke_error_boundary(error, parent)).finally(decrement_pending);
  }
  if (blocker_promise) {
    blocker_promise.then(() => {
      restore();
      run3();
      unset_context();
    });
  } else {
    run3();
  }
}
function capture() {
  var previous_effect = (
    /** @type {Effect} */
    active_effect
  );
  var previous_reaction = active_reaction;
  var previous_component_context = component_context;
  var previous_batch2 = (
    /** @type {Batch} */
    current_batch
  );
  if (dev_fallback_default) {
    var previous_dev_stack = dev_stack;
  }
  return function restore(activate_batch = true) {
    set_active_effect(previous_effect);
    set_active_reaction(previous_reaction);
    set_component_context(previous_component_context);
    if (activate_batch && (previous_effect.f & DESTROYED) === 0) {
      previous_batch2?.activate();
      previous_batch2?.apply();
    }
    if (dev_fallback_default) {
      set_reactivity_loss_tracker(null);
      set_dev_stack(previous_dev_stack);
    }
  };
}
var restored = false;
function unset_context(deactivate_batch = true) {
  restored = false;
  set_active_effect(null);
  set_active_reaction(null);
  set_component_context(null);
  if (deactivate_batch) current_batch?.deactivate();
  if (dev_fallback_default) {
    set_reactivity_loss_tracker(null);
    set_dev_stack(null);
  }
}
function increment_pending() {
  var effect2 = (
    /** @type {Effect} */
    active_effect
  );
  var boundary2 = effect2.b;
  var batch = (
    /** @type {Batch} */
    current_batch
  );
  var blocking = !!boundary2?.is_rendered();
  boundary2?.update_pending_count(1, batch);
  batch.increment(blocking, effect2);
  return () => {
    boundary2?.update_pending_count(-1, batch);
    batch.decrement(blocking, effect2);
  };
}

// node_modules/svelte/src/internal/client/reactivity/deriveds.js
var reactivity_loss_tracker = null;
function set_reactivity_loss_tracker(v) {
  reactivity_loss_tracker = v;
}
var recent_async_deriveds = /* @__PURE__ */ new Set();
// @__NO_SIDE_EFFECTS__
function derived(fn) {
  var flags2 = DERIVED | DIRTY;
  if (active_effect !== null) {
    active_effect.f |= EFFECT_PRESERVED;
  }
  const signal = {
    ctx: component_context,
    deps: null,
    effects: null,
    equals,
    f: flags2,
    fn,
    reactions: null,
    rv: 0,
    v: (
      /** @type {V} */
      UNINITIALIZED
    ),
    wv: 0,
    parent: active_effect,
    ac: null
  };
  if (dev_fallback_default && tracing_mode_flag) {
    signal.created = get_error("created at");
  }
  return signal;
}
var OBSOLETE = Symbol("obsolete");
// @__NO_SIDE_EFFECTS__
function async_derived(fn, label, location) {
  let parent = (
    /** @type {Effect | null} */
    active_effect
  );
  if (parent === null) {
    async_derived_orphan();
  }
  var promise = (
    /** @type {Promise<V>} */
    /** @type {unknown} */
    void 0
  );
  var signal = source(
    /** @type {V} */
    UNINITIALIZED
  );
  if (dev_fallback_default) signal.label = label ?? fn.toString();
  var should_suspend = !active_reaction;
  var deferreds = /* @__PURE__ */ new Set();
  async_effect(() => {
    var effect2 = (
      /** @type {Effect} */
      active_effect
    );
    if (dev_fallback_default) {
      reactivity_loss_tracker = { effect: effect2, effect_deps: /* @__PURE__ */ new Set(), warned: false };
    }
    var d = deferred();
    promise = d.promise;
    try {
      Promise.resolve(fn()).then(d.resolve, (e) => {
        if (e !== STALE_REACTION) d.reject(e);
      }).finally(unset_context);
    } catch (error) {
      d.reject(error);
      unset_context();
    }
    if (dev_fallback_default) {
      if (reactivity_loss_tracker) {
        if (effect2.deps !== null) {
          for (let i = 0; i < skipped_deps; i += 1) {
            reactivity_loss_tracker.effect_deps.add(effect2.deps[i]);
          }
        }
        if (new_deps !== null) {
          for (let i = 0; i < new_deps.length; i += 1) {
            reactivity_loss_tracker.effect_deps.add(new_deps[i]);
          }
        }
      }
      reactivity_loss_tracker = null;
    }
    var batch = (
      /** @type {Batch} */
      current_batch
    );
    if (should_suspend) {
      if ((effect2.f & REACTION_RAN) !== 0) {
        var decrement_pending = increment_pending();
      }
      if (
        // boundary can be null if the async derived is inside an $effect.root not connected to the component render tree
        parent.b?.is_rendered()
      ) {
        batch.async_deriveds.get(effect2)?.reject(OBSOLETE);
      } else {
        for (const d2 of deferreds.values()) {
          d2.reject(OBSOLETE);
        }
      }
      deferreds.add(d);
      batch.async_deriveds.set(effect2, d);
    }
    const handler = (value, error = void 0) => {
      if (dev_fallback_default) {
        reactivity_loss_tracker = null;
      }
      decrement_pending?.();
      deferreds.delete(d);
      if (error === OBSOLETE) return;
      batch.activate();
      if (error) {
        signal.f |= ERROR_VALUE;
        internal_set(signal, error);
      } else {
        if ((signal.f & ERROR_VALUE) !== 0) {
          signal.f ^= ERROR_VALUE;
        }
        if (dev_fallback_default && location !== void 0 && !signal.equals(value)) {
          recent_async_deriveds.add(signal);
          setTimeout(() => {
            if (recent_async_deriveds.has(signal) && (effect2.f & DESTROYED) === 0) {
              await_waterfall(
                /** @type {string} */
                signal.label,
                location
              );
              recent_async_deriveds.delete(signal);
            }
          });
        }
        internal_set(signal, value);
      }
      batch.deactivate();
    };
    d.promise.then(handler, (e) => handler(null, e || "unknown"));
  });
  teardown(() => {
    for (const d of deferreds) {
      d.reject(OBSOLETE);
    }
  });
  if (dev_fallback_default) {
    signal.f |= ASYNC;
  }
  return new Promise((fulfil) => {
    function next2(p) {
      function go() {
        if (p === promise) {
          fulfil(signal);
        } else {
          next2(promise);
        }
      }
      p.then(go, go);
    }
    next2(promise);
  });
}
// @__NO_SIDE_EFFECTS__
function user_derived(fn) {
  const d = /* @__PURE__ */ derived(fn);
  if (!async_mode_flag) push_reaction_value(d);
  return d;
}
// @__NO_SIDE_EFFECTS__
function derived_safe_equal(fn) {
  const signal = /* @__PURE__ */ derived(fn);
  signal.equals = safe_equals;
  return signal;
}
function destroy_derived_effects(derived2) {
  var effects = derived2.effects;
  if (effects !== null) {
    derived2.effects = null;
    for (var i = 0; i < effects.length; i += 1) {
      destroy_effect(
        /** @type {Effect} */
        effects[i]
      );
    }
  }
}
var stack = [];
function execute_derived(derived2) {
  var value;
  var prev_active_effect = active_effect;
  var parent = derived2.parent;
  if (!is_destroying_effect && parent !== null && derived2.v !== UNINITIALIZED && // if it was never evaluated before, it's guaranteed to fail downstream, so we try to execute instead
  (parent.f & (DESTROYED | INERT)) !== 0) {
    derived_inert();
    return derived2.v;
  }
  set_active_effect(parent);
  if (dev_fallback_default) {
    let prev_eager_effects = eager_effects;
    set_eager_effects(/* @__PURE__ */ new Set());
    try {
      if (includes.call(stack, derived2)) {
        derived_references_self();
      }
      stack.push(derived2);
      destroy_derived_effects(derived2);
      value = update_reaction(derived2);
    } finally {
      set_active_effect(prev_active_effect);
      set_eager_effects(prev_eager_effects);
      stack.pop();
    }
  } else {
    try {
      destroy_derived_effects(derived2);
      value = update_reaction(derived2);
    } finally {
      set_active_effect(prev_active_effect);
    }
  }
  return value;
}
function update_derived(derived2) {
  var value = execute_derived(derived2);
  if (!derived2.equals(value)) {
    derived2.wv = increment_write_version();
    if (!current_batch?.is_fork || derived2.deps === null) {
      if (current_batch !== null) {
        current_batch.capture(derived2, value, true);
        previous_batch?.capture(derived2, value, true);
      } else {
        derived2.v = value;
      }
      if (derived2.deps === null) {
        set_signal_status(derived2, CLEAN);
        return;
      }
    }
  }
  if (is_destroying_effect) {
    return;
  }
  if (batch_values !== null) {
    if (effect_tracking() || current_batch?.is_fork) {
      batch_values.set(derived2, value);
    }
  } else {
    update_derived_status(derived2);
  }
}
function freeze_derived_effects(derived2) {
  if (derived2.effects === null) return;
  for (const e of derived2.effects) {
    if (e.teardown || e.ac) {
      e.teardown?.();
      if (e.ac !== null) {
        without_reactive_context(() => {
          e.ac.abort(STALE_REACTION);
          e.ac = null;
        });
      }
      if (e.fn !== null) e.teardown = noop;
      remove_reactions(e, 0);
      destroy_effect_children(e);
    }
  }
}
function unfreeze_derived_effects(derived2) {
  if (derived2.effects === null) return;
  for (const e of derived2.effects) {
    if (e.teardown && e.fn !== null) {
      update_effect(e);
    }
  }
}

// node_modules/svelte/src/internal/client/reactivity/batch.js
var first_batch = null;
var last_batch = null;
var current_batch = null;
var previous_batch = null;
var batch_values = null;
var last_scheduled_effect = null;
var is_flushing_sync = false;
var is_processing = false;
var collected_effects = null;
var legacy_updates = null;
var flush_count = 0;
var source_stacks = /* @__PURE__ */ new Set();
var uid = 1;
var Batch = class _Batch {
  id = uid++;
  /** True as soon as `#process` was called */
  #started = false;
  linked = true;
  /** @type {Batch | null} */
  #prev = null;
  /** @type {Batch | null} */
  #next = null;
  /** @type {Map<Effect, ReturnType<typeof deferred<any>>>} */
  async_deriveds = /* @__PURE__ */ new Map();
  /**
   * The current values of any signals that are updated in this batch.
   * Tuple format: [value, is_derived] (note: is_derived is false for deriveds, too, if they were overridden via assignment)
   * They keys of this map are identical to `this.#previous`
   * @type {Map<Value, [any, boolean]>}
   */
  current = /* @__PURE__ */ new Map();
  /**
   * The values of any signals (sources and deriveds) that are updated in this batch _before_ those updates took place.
   * They keys of this map are identical to `this.#current`
   * @type {Map<Value, any>}
   */
  previous = /* @__PURE__ */ new Map();
  /**
   * When the batch is committed (and the DOM is updated), we need to remove old branches
   * and append new ones by calling the functions added inside (if/each/key/etc) blocks
   * @type {Set<(batch: Batch) => void>}
   */
  #commit_callbacks = /* @__PURE__ */ new Set();
  /**
   * If a fork is discarded, we need to destroy any effects that are no longer needed
   * @type {Set<(batch: Batch) => void>}
   */
  #discard_callbacks = /* @__PURE__ */ new Set();
  /**
   * The number of async effects that are currently in flight
   */
  #pending = 0;
  /**
   * Async effects that are currently in flight, _not_ inside a pending boundary
   * @type {Map<Effect, number>}
   */
  #blocking_pending = /* @__PURE__ */ new Map();
  /**
   * A deferred that resolves when the batch is committed, used with `settled()`
   * TODO replace with Promise.withResolvers once supported widely enough
   * @type {{ promise: Promise<void>, resolve: (value?: any) => void, reject: (reason: unknown) => void } | null}
   */
  #deferred = null;
  /**
   * Effects that were scheduled in this batch but not yet 'resolved' into the
   * root effects that need to be flushed. Resolving — the upwards traversal that
   * marks the path to each effect on the shared effect tree (see #resolve) — is
   * deferred until the batch is processed, so that the markers are created and
   * consumed within a single traversal. Scheduling into other batches (which can
   * happen concurrently, e.g. while a batch is committed) can therefore never
   * observe (and be confused by) this batch's markers.
   * May contain duplicates — deduplication happens during resolving
   * @type {Effect[]}
   */
  #scheduled = [];
  /**
   * Effects created while this batch was active.
   * @type {Effect[]}
   */
  #new_effects = [];
  /**
   * Deferred effects (which run after async work has completed) that are DIRTY
   * @type {Set<Effect>}
   */
  #dirty_effects = /* @__PURE__ */ new Set();
  /**
   * Deferred effects that are MAYBE_DIRTY
   * @type {Set<Effect>}
   */
  #maybe_dirty_effects = /* @__PURE__ */ new Set();
  /**
   * A map of branches that still exist, but will be destroyed when this batch
   * is committed — we skip over these during `process`.
   * The value contains child effects that were dirty/maybe_dirty before being reset,
   * so they can be rescheduled if the branch survives.
   * @type {Map<Effect, { d: Effect[], m: Effect[] }>}
   */
  #skipped_branches = /* @__PURE__ */ new Map();
  /**
   * Inverse of #skipped_branches which we need to tell prior batches to unskip them when committing
   * @type {Set<Effect>}
   */
  #unskipped_branches = /* @__PURE__ */ new Set();
  is_fork = false;
  #decrement_queued = false;
  constructor() {
    if (last_batch === null) {
      first_batch = last_batch = this;
    } else {
      last_batch.#next = this;
      this.#prev = last_batch;
    }
    last_batch = this;
  }
  #is_deferred() {
    if (this.is_fork) return true;
    for (const effect2 of this.#blocking_pending.keys()) {
      var e = effect2;
      var skipped = false;
      while (e.parent !== null) {
        if (this.#skipped_branches.has(e)) {
          skipped = true;
          break;
        }
        e = e.parent;
      }
      if (!skipped) {
        return true;
      }
    }
    return false;
  }
  /**
   * Add an effect to the #skipped_branches map and reset its children
   * @param {Effect} effect
   */
  skip_effect(effect2) {
    if (!this.#skipped_branches.has(effect2)) {
      this.#skipped_branches.set(effect2, { d: [], m: [] });
    }
    this.#unskipped_branches.delete(effect2);
  }
  /**
   * Remove an effect from the #skipped_branches map and reschedule
   * any tracked dirty/maybe_dirty child effects
   * @param {Effect} effect
   * @param {(e: Effect) => void} callback
   */
  unskip_effect(effect2, callback = (e) => this.schedule(e)) {
    var tracked = this.#skipped_branches.get(effect2);
    if (tracked) {
      this.#skipped_branches.delete(effect2);
      for (var e of tracked.d) {
        set_signal_status(e, DIRTY);
        callback(e);
      }
      for (e of tracked.m) {
        set_signal_status(e, MAYBE_DIRTY);
        callback(e);
      }
    }
    this.#unskipped_branches.add(effect2);
  }
  /**
   * Convert the effects that were scheduled in this batch into the root effects
   * that need to be traversed, marking the path to each effect (by clearing the
   * `CLEAN` flag on ancestor branches) so that the traversal can find them.
   * This happens right before traversal rather than at scheduling time, so that
   * the markers left on the (shared) effect tree are created and consumed within
   * a single traversal — scheduling into other batches can never observe them
   * @returns {Effect[]}
   */
  #resolve() {
    var roots = [];
    for (const effect2 of this.#scheduled) {
      if ((effect2.f & DESTROYED) !== 0 || (effect2.f & (DIRTY | MAYBE_DIRTY)) === 0) continue;
      var e = effect2;
      var covered = false;
      while (e.parent !== null) {
        e = e.parent;
        var flags2 = e.f;
        if ((flags2 & (ROOT_EFFECT | BRANCH_EFFECT)) !== 0) {
          if ((flags2 & CLEAN) === 0) {
            covered = true;
            break;
          }
          e.f ^= CLEAN;
        }
      }
      if (!covered) {
        roots.push(e);
      }
    }
    this.#scheduled = [];
    return roots;
  }
  #process() {
    this.#started = true;
    if (dev_fallback_default) {
      for (const value of this.current.keys()) {
        source_stacks.add(value);
      }
    }
    for (const e of this.#dirty_effects) {
      this.#maybe_dirty_effects.delete(e);
      set_signal_status(e, DIRTY);
      this.schedule(e);
    }
    for (const e of this.#maybe_dirty_effects) {
      set_signal_status(e, MAYBE_DIRTY);
      this.schedule(e);
    }
    this.apply();
    var effects = collected_effects = [];
    var render_effects = [];
    var updates = legacy_updates = [];
    while (this.#scheduled.length > 0) {
      if (flush_count++ > 1e3) {
        this.#unlink();
        infinite_loop_guard();
      }
      for (const root6 of this.#resolve()) {
        try {
          this.#traverse(root6, effects, render_effects);
        } catch (e) {
          reset_all(root6);
          if (!this.#is_deferred()) this.discard();
          throw e;
        }
      }
    }
    current_batch = null;
    if (updates.length > 0) {
      var batch = _Batch.ensure();
      for (const e of updates) {
        batch.schedule(e);
      }
    }
    collected_effects = null;
    legacy_updates = null;
    if (this.#is_deferred()) {
      this.#defer_effects(render_effects);
      this.#defer_effects(effects);
      for (const [e, t] of this.#skipped_branches) {
        reset_branch(e, t);
      }
      if (updates.length > 0) {
        /** @type {unknown} */
        current_batch.#process();
      }
      return;
    }
    const earlier_batch = this.#find_earlier_batch();
    if (earlier_batch) {
      this.#defer_effects(render_effects);
      this.#defer_effects(effects);
      earlier_batch.#merge(this);
      return;
    }
    this.#dirty_effects.clear();
    this.#maybe_dirty_effects.clear();
    for (const fn of this.#commit_callbacks) fn(this);
    this.#commit_callbacks.clear();
    previous_batch = this;
    flush_queued_effects(render_effects);
    flush_queued_effects(effects);
    previous_batch = null;
    this.#deferred?.resolve();
    var next_batch = (
      /** @type {Batch | null} */
      /** @type {unknown} */
      current_batch
    );
    if (this.#pending === 0 && (this.#scheduled.length === 0 || next_batch !== null)) {
      this.#unlink();
      if (async_mode_flag) {
        this.#commit();
        current_batch = next_batch;
      }
    }
    if (this.#scheduled.length > 0) {
      if (next_batch !== null) {
        for (const e of this.#scheduled) {
          next_batch.#scheduled.push(e);
        }
        this.#scheduled = [];
      } else {
        next_batch = this;
      }
    }
    if (next_batch !== null) {
      old_values.clear();
      next_batch.#process();
    }
  }
  /**
   * Traverse the effect tree, executing effects or stashing
   * them for later execution as appropriate
   * @param {Effect} root
   * @param {Effect[]} effects
   * @param {Effect[]} render_effects
   */
  #traverse(root6, effects, render_effects) {
    root6.f ^= CLEAN;
    var effect2 = root6.first;
    while (effect2 !== null) {
      var flags2 = effect2.f;
      var is_branch = (flags2 & (BRANCH_EFFECT | ROOT_EFFECT)) !== 0;
      var is_skippable_branch = is_branch && (flags2 & CLEAN) !== 0;
      var skip = is_skippable_branch || (flags2 & INERT) !== 0 || this.#skipped_branches.has(effect2);
      if (!skip && effect2.fn !== null) {
        if (is_branch) {
          effect2.f ^= CLEAN;
        } else if ((flags2 & EFFECT) !== 0) {
          effects.push(effect2);
        } else if (async_mode_flag && (flags2 & (RENDER_EFFECT | MANAGED_EFFECT)) !== 0) {
          render_effects.push(effect2);
        } else if (is_dirty(effect2)) {
          if ((flags2 & BLOCK_EFFECT) !== 0) this.#maybe_dirty_effects.add(effect2);
          update_effect(effect2);
        }
        var child2 = effect2.first;
        if (child2 !== null) {
          effect2 = child2;
          continue;
        }
      }
      while (effect2 !== null) {
        var next2 = effect2.next;
        if (next2 !== null) {
          effect2 = next2;
          break;
        }
        effect2 = effect2.parent;
      }
    }
  }
  #find_earlier_batch() {
    var batch = this.#prev;
    while (batch !== null) {
      if (!batch.is_fork) {
        for (const [value, [, is_derived]] of this.current) {
          if (batch.current.has(value) && !is_derived) {
            return batch;
          }
        }
      }
      batch = batch.#prev;
    }
    return null;
  }
  /**
   * @param {Batch} batch
   */
  #merge(batch) {
    for (const [source2, value] of batch.current) {
      if (!this.previous.has(source2) && batch.previous.has(source2)) {
        this.previous.set(source2, batch.previous.get(source2));
      }
      this.current.set(source2, value);
    }
    for (const [effect2, deferred2] of batch.async_deriveds) {
      const d = this.async_deriveds.get(effect2);
      if (d) deferred2.promise.then(d.resolve).catch(d.reject);
    }
    batch.async_deriveds.clear();
    this.transfer_effects(batch.#dirty_effects, batch.#maybe_dirty_effects);
    const mark = (value) => {
      var reactions = value.reactions;
      if (reactions === null) return;
      if ((value.f & DERIVED) !== 0 && (value.f & (DIRTY | MAYBE_DIRTY)) === 0) {
        return;
      }
      for (const reaction of reactions) {
        var flags2 = reaction.f;
        if ((flags2 & DERIVED) !== 0) {
          mark(
            /** @type {Derived} */
            reaction
          );
        } else {
          var effect2 = (
            /** @type {Effect} */
            reaction
          );
          if (flags2 & (ASYNC | BLOCK_EFFECT) && !this.async_deriveds.has(effect2)) {
            this.#maybe_dirty_effects.delete(effect2);
            set_signal_status(effect2, DIRTY);
            this.schedule(effect2);
          }
        }
      }
    };
    for (const source2 of this.current.keys()) {
      mark(source2);
    }
    this.oncommit(() => batch.discard());
    batch.#unlink();
    current_batch = this;
    this.#process();
  }
  /**
   * @param {Effect[]} effects
   */
  #defer_effects(effects) {
    for (var i = 0; i < effects.length; i += 1) {
      defer_effect(effects[i], this.#dirty_effects, this.#maybe_dirty_effects);
    }
  }
  /**
   * Associate a change to a given source with the current
   * batch, noting its previous and current values
   * @param {Value} source
   * @param {any} value
   * @param {boolean} [is_derived]
   */
  capture(source2, value, is_derived = false) {
    if (source2.v !== UNINITIALIZED && !this.previous.has(source2)) {
      this.previous.set(source2, source2.v);
    }
    if ((source2.f & ERROR_VALUE) === 0) {
      this.current.set(source2, [value, is_derived]);
      batch_values?.set(source2, value);
    }
    if (!this.is_fork) {
      source2.v = value;
    }
  }
  activate() {
    current_batch = this;
  }
  deactivate() {
    current_batch = null;
    batch_values = null;
  }
  flush() {
    try {
      if (dev_fallback_default) {
        source_stacks.clear();
      }
      is_processing = true;
      current_batch = this;
      this.#process();
    } finally {
      flush_count = 0;
      last_scheduled_effect = null;
      collected_effects = null;
      legacy_updates = null;
      is_processing = false;
      current_batch = null;
      batch_values = null;
      old_values.clear();
      if (dev_fallback_default) {
        for (const source2 of source_stacks) {
          source2.updated = null;
        }
      }
    }
  }
  discard() {
    for (const fn of this.#discard_callbacks) fn(this);
    this.#discard_callbacks.clear();
    for (const deferred2 of this.async_deriveds.values()) {
      deferred2.reject(OBSOLETE);
    }
    this.#unlink();
    this.#deferred?.resolve();
  }
  /**
   * @param {Effect} effect
   */
  register_created_effect(effect2) {
    this.#new_effects.push(effect2);
  }
  #commit() {
    for (let batch = first_batch; batch !== null; batch = batch.#next) {
      var is_earlier = batch.id < this.id;
      var sources = [];
      for (const [source3, [value, is_derived]] of this.current) {
        if (batch.current.has(source3)) {
          var batch_value = (
            /** @type {[any, boolean]} */
            batch.current.get(source3)[0]
          );
          if (is_earlier && value !== batch_value) {
            batch.current.set(source3, [value, is_derived]);
          } else {
            continue;
          }
        }
        sources.push(source3);
      }
      if (is_earlier) {
        for (const [effect2, deferred2] of this.async_deriveds) {
          const d = batch.async_deriveds.get(effect2);
          if (d) deferred2.promise.then(d.resolve).catch(d.reject);
        }
      }
      var current = [...batch.current.keys()].filter(
        (source3) => !/** @type {[any, boolean]} */
        batch.current.get(source3)[1]
      );
      if (!batch.#started || current.length === 0) continue;
      var others = current.filter((source3) => !this.current.has(source3));
      if (others.length === 0) {
        if (is_earlier) {
          batch.discard();
        }
      } else if (sources.length > 0) {
        if (dev_fallback_default && !batch.#decrement_queued) {
          invariant(batch.#scheduled.length === 0, "Batch has scheduled effects");
        }
        if (is_earlier) {
          for (const unskipped of this.#unskipped_branches) {
            batch.unskip_effect(unskipped, (e) => {
              if ((e.f & (BLOCK_EFFECT | ASYNC)) !== 0) {
                batch.schedule(e);
              } else {
                batch.#defer_effects([e]);
              }
            });
          }
        }
        batch.activate();
        var marked = /* @__PURE__ */ new Set();
        var checked = /* @__PURE__ */ new Map();
        for (var source2 of sources) {
          mark_effects(source2, others, marked, checked);
        }
        checked = /* @__PURE__ */ new Map();
        var current_unequal = [...batch.current].filter(([c, v1]) => {
          const v2 = this.current.get(c);
          if (!v2) return true;
          return v2[0] !== v1[0] || v2[1] !== v1[1];
        }).map(([c]) => c);
        if (current_unequal.length > 0) {
          for (const effect2 of this.#new_effects) {
            if ((effect2.f & (DESTROYED | INERT | EAGER_EFFECT)) === 0 && depends_on(effect2, current_unequal, checked)) {
              if ((effect2.f & (ASYNC | BLOCK_EFFECT)) !== 0) {
                set_signal_status(effect2, DIRTY);
                batch.schedule(effect2);
              } else {
                batch.#dirty_effects.add(effect2);
              }
            }
          }
        }
        if (batch.#scheduled.length > 0 && !batch.#decrement_queued) {
          batch.apply();
          for (var root6 of batch.#resolve()) {
            batch.#traverse(root6, [], []);
          }
        }
        batch.deactivate();
      }
    }
  }
  /**
   * @param {boolean} blocking
   * @param {Effect} effect
   */
  increment(blocking, effect2) {
    this.#pending += 1;
    if (blocking) {
      let blocking_pending_count = this.#blocking_pending.get(effect2) ?? 0;
      this.#blocking_pending.set(effect2, blocking_pending_count + 1);
    }
  }
  /**
   * @param {boolean} blocking
   * @param {Effect} effect
   */
  decrement(blocking, effect2) {
    this.#pending -= 1;
    if (blocking) {
      let blocking_pending_count = this.#blocking_pending.get(effect2) ?? 0;
      if (blocking_pending_count === 1) {
        this.#blocking_pending.delete(effect2);
      } else {
        this.#blocking_pending.set(effect2, blocking_pending_count - 1);
      }
    }
    if (this.#decrement_queued) return;
    this.#decrement_queued = true;
    queue_micro_task(() => {
      this.#decrement_queued = false;
      if (this.linked) {
        this.flush();
      }
    });
  }
  /**
   * @param {Set<Effect>} dirty_effects
   * @param {Set<Effect>} maybe_dirty_effects
   */
  transfer_effects(dirty_effects, maybe_dirty_effects) {
    for (const e of dirty_effects) {
      this.#dirty_effects.add(e);
    }
    for (const e of maybe_dirty_effects) {
      this.#maybe_dirty_effects.add(e);
    }
    dirty_effects.clear();
    maybe_dirty_effects.clear();
  }
  /** @param {(batch: Batch) => void} fn */
  oncommit(fn) {
    this.#commit_callbacks.add(fn);
  }
  /** @param {(batch: Batch) => void} fn */
  ondiscard(fn) {
    this.#discard_callbacks.add(fn);
  }
  settled() {
    return (this.#deferred ??= deferred()).promise;
  }
  static ensure() {
    if (current_batch === null) {
      const batch = current_batch = new _Batch();
      if (!is_processing && !is_flushing_sync) {
        queue_micro_task(() => {
          if (!batch.#started) {
            batch.flush();
          }
        });
      }
    }
    return current_batch;
  }
  apply() {
    if (!async_mode_flag || !this.is_fork && this.#prev === null && this.#next === null) {
      batch_values = null;
      return;
    }
    batch_values = /* @__PURE__ */ new Map();
    for (const [source2, [value]] of this.current) {
      batch_values.set(source2, value);
    }
    for (let batch = first_batch; batch !== null; batch = batch.#next) {
      if (batch === this || batch.is_fork) continue;
      var intersects = false;
      if (batch.id < this.id) {
        for (const [source2, [, is_derived]] of batch.current) {
          if (is_derived) continue;
          if (this.current.has(source2)) {
            intersects = true;
            break;
          }
        }
      }
      if (!intersects) {
        for (const [source2, previous] of batch.previous) {
          if (!batch_values.has(source2)) {
            batch_values.set(source2, previous);
          }
        }
      }
    }
  }
  /**
   *
   * @param {Effect} effect
   */
  schedule(effect2) {
    last_scheduled_effect = effect2;
    if (effect2.b?.is_pending && (effect2.f & (EFFECT | RENDER_EFFECT | MANAGED_EFFECT)) !== 0 && (effect2.f & REACTION_RAN) === 0) {
      effect2.b.defer_effect(effect2);
      return;
    }
    this.#scheduled.push(effect2);
  }
  #unlink() {
    if (!this.linked) return;
    var prev = this.#prev;
    var next2 = this.#next;
    if (prev === null) {
      first_batch = next2;
    } else {
      prev.#next = next2;
    }
    if (next2 === null) {
      last_batch = prev;
    } else {
      next2.#prev = prev;
    }
    this.linked = false;
  }
};
function flushSync(fn) {
  var was_flushing_sync = is_flushing_sync;
  is_flushing_sync = true;
  try {
    var result;
    if (fn) {
      if (current_batch !== null && !current_batch.is_fork) {
        current_batch.flush();
      }
      result = fn();
    }
    while (true) {
      flush_tasks();
      if (current_batch === null) {
        return (
          /** @type {T} */
          result
        );
      }
      current_batch.flush();
    }
  } finally {
    is_flushing_sync = was_flushing_sync;
  }
}
function infinite_loop_guard() {
  if (dev_fallback_default) {
    var updates = /* @__PURE__ */ new Map();
    for (
      const source2 of
      /** @type {Batch} */
      current_batch.current.keys()
    ) {
      for (const [stack2, update2] of source2.updated ?? []) {
        var entry = updates.get(stack2);
        if (!entry) {
          entry = { error: update2.error, count: 0 };
          updates.set(stack2, entry);
        }
        entry.count += update2.count;
      }
    }
    for (const update2 of updates.values()) {
      if (update2.error) {
        console.error(update2.error);
      }
    }
  }
  try {
    effect_update_depth_exceeded();
  } catch (error) {
    if (dev_fallback_default) {
      define_property(error, "stack", { value: "" });
    }
    invoke_error_boundary(error, last_scheduled_effect);
  }
}
var eager_block_effects = null;
function flush_queued_effects(effects) {
  var length = effects.length;
  if (length === 0) return;
  var i = 0;
  while (i < length) {
    var effect2 = effects[i++];
    if ((effect2.f & (DESTROYED | INERT)) === 0 && is_dirty(effect2)) {
      eager_block_effects = /* @__PURE__ */ new Set();
      update_effect(effect2);
      if (effect2.deps === null && effect2.first === null && effect2.nodes === null && effect2.teardown === null && effect2.ac === null) {
        unlink_effect(effect2);
      }
      if (eager_block_effects?.size > 0) {
        old_values.clear();
        for (const e of eager_block_effects) {
          if ((e.f & (DESTROYED | INERT)) !== 0) continue;
          const ordered_effects = [e];
          let ancestor = e.parent;
          while (ancestor !== null) {
            if (eager_block_effects.has(ancestor)) {
              eager_block_effects.delete(ancestor);
              ordered_effects.push(ancestor);
            }
            ancestor = ancestor.parent;
          }
          for (let j = ordered_effects.length - 1; j >= 0; j--) {
            const e2 = ordered_effects[j];
            if ((e2.f & (DESTROYED | INERT)) !== 0) continue;
            update_effect(e2);
          }
        }
        eager_block_effects.clear();
      }
    }
  }
  eager_block_effects = null;
}
function mark_effects(value, sources, marked, checked) {
  if (marked.has(value)) return;
  marked.add(value);
  if (value.reactions !== null) {
    for (const reaction of value.reactions) {
      const flags2 = reaction.f;
      if ((flags2 & DERIVED) !== 0) {
        mark_effects(
          /** @type {Derived} */
          reaction,
          sources,
          marked,
          checked
        );
      } else if ((flags2 & (ASYNC | BLOCK_EFFECT)) !== 0 && (flags2 & DIRTY) === 0 && depends_on(reaction, sources, checked)) {
        set_signal_status(reaction, DIRTY);
        schedule_effect(
          /** @type {Effect} */
          reaction
        );
      }
    }
  }
}
function depends_on(reaction, sources, checked) {
  const depends = checked.get(reaction);
  if (depends !== void 0) return depends;
  if (reaction.deps !== null) {
    for (const dep of reaction.deps) {
      if (includes.call(sources, dep)) {
        return true;
      }
      if ((dep.f & DERIVED) !== 0 && depends_on(
        /** @type {Derived} */
        dep,
        sources,
        checked
      )) {
        checked.set(
          /** @type {Derived} */
          dep,
          true
        );
        return true;
      }
    }
  }
  checked.set(reaction, false);
  return false;
}
function schedule_effect(effect2) {
  current_batch.schedule(effect2);
}
function reset_branch(effect2, tracked) {
  if ((effect2.f & BRANCH_EFFECT) !== 0 && (effect2.f & CLEAN) !== 0) {
    return;
  }
  if ((effect2.f & DIRTY) !== 0) {
    tracked.d.push(effect2);
  } else if ((effect2.f & MAYBE_DIRTY) !== 0) {
    tracked.m.push(effect2);
  }
  set_signal_status(effect2, CLEAN);
  var e = effect2.first;
  while (e !== null) {
    reset_branch(e, tracked);
    e = e.next;
  }
}
function reset_all(effect2) {
  set_signal_status(effect2, CLEAN);
  var e = effect2.first;
  while (e !== null) {
    reset_all(e);
    e = e.next;
  }
}

// node_modules/svelte/src/internal/client/reactivity/sources.js
var eager_effects = /* @__PURE__ */ new Set();
var old_values = /* @__PURE__ */ new Map();
function set_eager_effects(v) {
  eager_effects = v;
}
var eager_effects_deferred = false;
function set_eager_effects_deferred() {
  eager_effects_deferred = true;
}
function source(v, stack2) {
  var signal = {
    f: 0,
    // TODO ideally we could skip this altogether, but it causes type errors
    v,
    reactions: null,
    equals,
    rv: 0,
    wv: 0
  };
  if (dev_fallback_default && tracing_mode_flag) {
    signal.created = stack2 ?? get_error("created at");
    signal.updated = null;
    signal.set_during_effect = false;
    signal.trace = null;
  }
  return signal;
}
// @__NO_SIDE_EFFECTS__
function state(v, stack2) {
  const s = source(v, stack2);
  push_reaction_value(s);
  return s;
}
// @__NO_SIDE_EFFECTS__
function mutable_source(initial_value, immutable = false, trackable = true) {
  const s = source(initial_value);
  if (!immutable) {
    s.equals = safe_equals;
  }
  if (legacy_mode_flag && trackable && component_context !== null && component_context.l !== null) {
    (component_context.l.s ??= []).push(s);
  }
  return s;
}
function mutate(source2, value) {
  set(
    source2,
    untrack(() => get(source2))
  );
  return value;
}
function set(source2, value, should_proxy = false) {
  if (active_reaction !== null && // since we are untracking the function inside `$inspect.with` we need to add this check
  // to ensure we error if state is set inside an inspect effect
  (!untracking || (active_reaction.f & EAGER_EFFECT) !== 0) && is_runes() && (active_reaction.f & (DERIVED | BLOCK_EFFECT | ASYNC | EAGER_EFFECT)) !== 0 && (current_sources === null || !current_sources.has(source2))) {
    state_unsafe_mutation();
  }
  let new_value = should_proxy ? proxy(value) : value;
  if (dev_fallback_default) {
    tag_proxy(
      new_value,
      /** @type {string} */
      source2.label
    );
  }
  return internal_set(source2, new_value, legacy_updates);
}
var seen = null;
var count_deps = 0;
function internal_set(source2, value, updated_during_traversal = null) {
  if (!source2.equals(value)) {
    if (is_destroying_effect) {
      old_values.set(source2, value);
    } else if (!old_values.has(source2)) {
      old_values.set(source2, source2.v);
    }
    var batch = Batch.ensure();
    batch.capture(source2, value);
    if (dev_fallback_default) {
      if (tracing_mode_flag || active_effect !== null) {
        source2.updated ??= /* @__PURE__ */ new Map();
        const count = (source2.updated.get("")?.count ?? 0) + 1;
        source2.updated.set("", { error: (
          /** @type {any} */
          null
        ), count });
        if (tracing_mode_flag || count > 5) {
          const error = get_error("updated at");
          if (error !== null) {
            let entry = source2.updated.get(error.stack);
            if (!entry) {
              entry = { error, count: 0 };
              source2.updated.set(error.stack, entry);
            }
            entry.count++;
          }
        }
      }
      if (active_effect !== null) {
        source2.set_during_effect = true;
      }
    }
    if ((source2.f & DERIVED) !== 0) {
      const derived2 = (
        /** @type {Derived} */
        source2
      );
      if ((source2.f & DIRTY) !== 0) {
        execute_derived(derived2);
      }
      if (batch_values === null) {
        update_derived_status(derived2);
      }
    }
    source2.wv = increment_write_version();
    seen = null;
    count_deps = 0;
    mark_reactions(source2, DIRTY, updated_during_traversal);
    seen = null;
    if (is_runes() && active_effect !== null && (active_effect.f & CLEAN) !== 0 && (active_effect.f & (BRANCH_EFFECT | ROOT_EFFECT)) === 0) {
      if (untracked_writes === null) {
        set_untracked_writes([source2]);
      } else {
        untracked_writes.push(source2);
      }
    }
    if (!batch.is_fork && eager_effects.size > 0 && !eager_effects_deferred) {
      flush_eager_effects();
    }
  }
  return value;
}
function flush_eager_effects() {
  eager_effects_deferred = false;
  for (const effect2 of eager_effects) {
    if ((effect2.f & CLEAN) !== 0) {
      set_signal_status(effect2, MAYBE_DIRTY);
    }
    let dirty;
    try {
      dirty = is_dirty(effect2);
    } catch {
      dirty = true;
    }
    if (dirty) {
      update_effect(effect2);
    }
  }
  eager_effects.clear();
}
function update(source2, d = 1) {
  var value = get(source2);
  var result = d === 1 ? value++ : value--;
  set(source2, value);
  return result;
}
function increment(source2) {
  set(source2, source2.v + 1);
}
function mark_reactions(signal, status, updated_during_traversal) {
  var reactions = signal.reactions;
  if (reactions === null) return;
  var runes = is_runes();
  var length = reactions.length;
  count_deps += length;
  if (count_deps > 1e5 && seen === null) seen = /* @__PURE__ */ new Set();
  if (seen !== null) {
    if (seen.has(signal)) return;
    seen.add(signal);
  }
  for (var i = 0; i < length; i++) {
    var reaction = reactions[i];
    var flags2 = reaction.f;
    if (!runes && reaction === active_effect) continue;
    var not_dirty = (flags2 & DIRTY) === 0;
    if (not_dirty) {
      set_signal_status(reaction, status);
    }
    if ((flags2 & EAGER_EFFECT) !== 0) {
      eager_effects.add(
        /** @type {Effect} */
        reaction
      );
    } else if ((flags2 & DERIVED) !== 0) {
      var derived2 = (
        /** @type {Derived} */
        reaction
      );
      batch_values?.delete(derived2);
      mark_reactions(derived2, MAYBE_DIRTY, updated_during_traversal);
    } else if (not_dirty) {
      var effect2 = (
        /** @type {Effect} */
        reaction
      );
      if ((flags2 & BLOCK_EFFECT) !== 0 && eager_block_effects !== null) {
        eager_block_effects.add(effect2);
      }
      if (updated_during_traversal !== null) {
        updated_during_traversal.push(effect2);
      } else {
        schedule_effect(effect2);
      }
    }
  }
}

// node_modules/svelte/src/internal/client/proxy.js
var regex_is_valid_identifier = /^[a-zA-Z_$][a-zA-Z_$0-9]*$/;
function proxy(value) {
  if (typeof value !== "object" || value === null || STATE_SYMBOL in value || COMPONENT_SYMBOL in value) {
    return value;
  }
  const prototype = get_prototype_of(value);
  if (prototype !== object_prototype && prototype !== array_prototype) {
    return value;
  }
  var sources = /* @__PURE__ */ new Map();
  var is_proxied_array = is_array(value);
  var version = state(0);
  var stack2 = dev_fallback_default && tracing_mode_flag ? get_error("created at") : null;
  var parent_version = update_version;
  var with_parent = (fn) => {
    if (update_version === parent_version) {
      return fn();
    }
    var reaction = active_reaction;
    var version2 = update_version;
    set_active_reaction(null);
    set_update_version(parent_version);
    var result = fn();
    set_active_reaction(reaction);
    set_update_version(version2);
    return result;
  };
  if (is_proxied_array) {
    sources.set("length", state(
      /** @type {any[]} */
      value.length,
      stack2
    ));
    if (dev_fallback_default) {
      value = /** @type {any} */
      inspectable_array(
        /** @type {any[]} */
        value
      );
    }
  }
  var path = "";
  let updating = false;
  function update_path(new_path) {
    if (updating) return;
    updating = true;
    path = new_path;
    tag(version, `${path} version`);
    for (const [prop2, source2] of sources) {
      tag(source2, get_label(path, prop2));
    }
    updating = false;
  }
  return new Proxy(
    /** @type {any} */
    value,
    {
      defineProperty(_, prop2, descriptor) {
        if (!("value" in descriptor) || descriptor.configurable === false || descriptor.enumerable === false || descriptor.writable === false) {
          state_descriptors_fixed();
        }
        var s = sources.get(prop2);
        if (s === void 0) {
          with_parent(() => {
            var s2 = state(descriptor.value, stack2);
            sources.set(prop2, s2);
            if (dev_fallback_default && typeof prop2 === "string") {
              tag(s2, get_label(path, prop2));
            }
            return s2;
          });
        } else {
          set(s, descriptor.value, true);
        }
        return true;
      },
      deleteProperty(target, prop2) {
        var s = sources.get(prop2);
        if (s === void 0) {
          if (prop2 in target) {
            const s2 = with_parent(() => state(UNINITIALIZED, stack2));
            sources.set(prop2, s2);
            increment(version);
            if (dev_fallback_default) {
              tag(s2, get_label(path, prop2));
            }
          }
        } else {
          set(s, UNINITIALIZED);
          increment(version);
        }
        return true;
      },
      get(target, prop2, receiver) {
        if (prop2 === STATE_SYMBOL) {
          return value;
        }
        if (dev_fallback_default && prop2 === PROXY_PATH_SYMBOL) {
          return update_path;
        }
        var s = sources.get(prop2);
        var exists = prop2 in target;
        if (s === void 0 && (!exists || get_descriptor(target, prop2)?.writable)) {
          s = with_parent(() => {
            var p = proxy(exists ? target[prop2] : UNINITIALIZED);
            var s2 = state(p, stack2);
            if (dev_fallback_default) {
              tag(s2, get_label(path, prop2));
            }
            return s2;
          });
          sources.set(prop2, s);
        }
        if (s !== void 0) {
          var v = get(s);
          return v === UNINITIALIZED ? void 0 : v;
        }
        return Reflect.get(target, prop2, receiver);
      },
      getOwnPropertyDescriptor(target, prop2) {
        this.has?.(target, prop2);
        var descriptor = Reflect.getOwnPropertyDescriptor(target, prop2);
        var s = sources.get(prop2);
        if (s !== void 0) {
          var value2 = get(s);
          if (value2 === UNINITIALIZED) {
            return void 0;
          }
          if (descriptor && "value" in descriptor) {
            descriptor.value = value2;
          } else {
            return {
              enumerable: true,
              configurable: true,
              value: value2,
              writable: true
            };
          }
        }
        return descriptor;
      },
      has(target, prop2) {
        if (prop2 === STATE_SYMBOL) {
          return true;
        }
        var s = sources.get(prop2);
        var has = s !== void 0 && s.v !== UNINITIALIZED || Reflect.has(target, prop2);
        if (s !== void 0 || active_effect !== null && (!has || get_descriptor(target, prop2)?.writable)) {
          if (s === void 0) {
            s = with_parent(() => {
              var p = has ? proxy(target[prop2]) : UNINITIALIZED;
              var s2 = state(p, stack2);
              if (dev_fallback_default) {
                tag(s2, get_label(path, prop2));
              }
              return s2;
            });
            sources.set(prop2, s);
          }
          var value2 = get(s);
          if (value2 === UNINITIALIZED) {
            return false;
          }
        }
        return has;
      },
      set(target, prop2, value2, receiver) {
        var s = sources.get(prop2);
        var has = prop2 in target;
        if (is_proxied_array && prop2 === "length") {
          for (var i = value2; i < /** @type {Source<number>} */
          s.v; i += 1) {
            var other_s = sources.get(i + "");
            if (other_s !== void 0) {
              set(other_s, UNINITIALIZED);
            } else if (i in target) {
              other_s = with_parent(() => state(UNINITIALIZED, stack2));
              sources.set(i + "", other_s);
              if (dev_fallback_default) {
                tag(other_s, get_label(path, i));
              }
            }
          }
        }
        if (s === void 0) {
          if (!has || get_descriptor(target, prop2)?.writable) {
            s = with_parent(() => state(void 0, stack2));
            if (dev_fallback_default) {
              tag(s, get_label(path, prop2));
            }
            set(s, proxy(value2));
            sources.set(prop2, s);
          }
        } else {
          has = s.v !== UNINITIALIZED;
          var p = with_parent(() => proxy(value2));
          set(s, p);
        }
        var descriptor = Reflect.getOwnPropertyDescriptor(target, prop2);
        if (descriptor?.set) {
          descriptor.set.call(receiver, value2);
        }
        if (!has) {
          if (is_proxied_array && typeof prop2 === "string") {
            var ls = (
              /** @type {Source<number>} */
              sources.get("length")
            );
            var n = Number(prop2);
            if (Number.isInteger(n) && n >= ls.v) {
              set(ls, n + 1);
            }
          }
          increment(version);
        }
        return true;
      },
      ownKeys(target) {
        get(version);
        var own_keys = Reflect.ownKeys(target).filter((key3) => {
          var source3 = sources.get(key3);
          return source3 === void 0 || source3.v !== UNINITIALIZED;
        });
        for (var [key2, source2] of sources) {
          if (source2.v !== UNINITIALIZED && !(key2 in target)) {
            own_keys.push(key2);
          }
        }
        return own_keys;
      },
      setPrototypeOf() {
        state_prototype_fixed();
      }
    }
  );
}
function get_label(path, prop2) {
  if (typeof prop2 === "symbol") return `${path}[Symbol(${prop2.description ?? ""})]`;
  if (regex_is_valid_identifier.test(prop2)) return `${path}.${prop2}`;
  return /^\d+$/.test(prop2) ? `${path}[${prop2}]` : `${path}['${prop2}']`;
}
function get_proxied_value(value) {
  try {
    if (value !== null && typeof value === "object" && STATE_SYMBOL in value) {
      return value[STATE_SYMBOL];
    }
  } catch {
  }
  return value;
}
function is(a, b) {
  return Object.is(get_proxied_value(a), get_proxied_value(b));
}
var ARRAY_MUTATING_METHODS = /* @__PURE__ */ new Set([
  "copyWithin",
  "fill",
  "pop",
  "push",
  "reverse",
  "shift",
  "sort",
  "splice",
  "unshift"
]);
function inspectable_array(array) {
  return new Proxy(array, {
    get(target, prop2, receiver) {
      var value = Reflect.get(target, prop2, receiver);
      if (!ARRAY_MUTATING_METHODS.has(
        /** @type {string} */
        prop2
      )) {
        return value;
      }
      return function(...args) {
        set_eager_effects_deferred();
        var result = value.apply(this, args);
        flush_eager_effects();
        return result;
      };
    }
  });
}

// node_modules/svelte/src/internal/client/dev/equality.js
function init_array_prototype_warnings() {
  const array_prototype2 = Array.prototype;
  const cleanup = Array.__svelte_cleanup;
  if (cleanup) {
    cleanup();
  }
  const { indexOf, lastIndexOf, includes: includes2 } = array_prototype2;
  array_prototype2.indexOf = function(item, from_index) {
    const index2 = indexOf.call(this, item, from_index);
    if (index2 === -1) {
      for (let i = from_index ?? 0; i < this.length; i += 1) {
        if (get_proxied_value(this[i]) === item) {
          state_proxy_equality_mismatch("array.indexOf(...)");
          break;
        }
      }
    }
    return index2;
  };
  array_prototype2.lastIndexOf = function(item, from_index) {
    const index2 = lastIndexOf.call(this, item, from_index ?? this.length - 1);
    if (index2 === -1) {
      for (let i = 0; i <= (from_index ?? this.length - 1); i += 1) {
        if (get_proxied_value(this[i]) === item) {
          state_proxy_equality_mismatch("array.lastIndexOf(...)");
          break;
        }
      }
    }
    return index2;
  };
  array_prototype2.includes = function(item, from_index) {
    const has = includes2.call(this, item, from_index);
    if (!has) {
      for (let i = 0; i < this.length; i += 1) {
        if (get_proxied_value(this[i]) === item) {
          state_proxy_equality_mismatch("array.includes(...)");
          break;
        }
      }
    }
    return has;
  };
  Array.__svelte_cleanup = () => {
    array_prototype2.indexOf = indexOf;
    array_prototype2.lastIndexOf = lastIndexOf;
    array_prototype2.includes = includes2;
  };
}

// node_modules/svelte/src/internal/client/dom/operations.js
var $window;
var $document;
var is_firefox;
var first_child_getter;
var next_sibling_getter;
function init_operations() {
  if ($window !== void 0) {
    return;
  }
  $window = window;
  $document = document;
  is_firefox = /Firefox/.test(navigator.userAgent);
  var element_prototype = Element.prototype;
  var node_prototype = Node.prototype;
  var text_prototype = Text.prototype;
  first_child_getter = get_descriptor(node_prototype, "firstChild").get;
  next_sibling_getter = get_descriptor(node_prototype, "nextSibling").get;
  if (is_extensible(element_prototype)) {
    element_prototype[CLASS_CACHE] = void 0;
    element_prototype[ATTRIBUTES_CACHE] = null;
    element_prototype[STYLE_CACHE] = void 0;
    element_prototype.__e = void 0;
  }
  if (is_extensible(text_prototype)) {
    text_prototype[TEXT_CACHE] = void 0;
  }
  if (dev_fallback_default) {
    element_prototype.__svelte_meta = null;
    init_array_prototype_warnings();
  }
}
function create_text(value = "") {
  return document.createTextNode(value);
}
// @__NO_SIDE_EFFECTS__
function get_first_child(node) {
  return (
    /** @type {TemplateNode | null} */
    first_child_getter.call(node)
  );
}
// @__NO_SIDE_EFFECTS__
function get_next_sibling(node) {
  return (
    /** @type {TemplateNode | null} */
    next_sibling_getter.call(node)
  );
}
function child(node, is_text) {
  if (!hydrating) {
    return /* @__PURE__ */ get_first_child(node);
  }
  var child2 = /* @__PURE__ */ get_first_child(hydrate_node);
  if (child2 === null) {
    child2 = hydrate_node.appendChild(create_text());
  } else if (is_text && child2.nodeType !== TEXT_NODE) {
    var text2 = create_text();
    child2?.before(text2);
    set_hydrate_node(text2);
    return text2;
  }
  if (is_text) {
    merge_text_nodes(
      /** @type {Text} */
      child2
    );
  }
  set_hydrate_node(child2);
  return child2;
}
function first_child(node, is_text = false) {
  if (!hydrating) {
    var first = /* @__PURE__ */ get_first_child(node);
    if (first instanceof Comment && first.data === "") return /* @__PURE__ */ get_next_sibling(first);
    return first;
  }
  if (is_text) {
    if (hydrate_node?.nodeType !== TEXT_NODE) {
      var text2 = create_text();
      hydrate_node?.before(text2);
      set_hydrate_node(text2);
      return text2;
    }
    merge_text_nodes(
      /** @type {Text} */
      hydrate_node
    );
  }
  return hydrate_node;
}
function only_child(node, is_text = false) {
  if (!hydrating) {
    return /* @__PURE__ */ get_first_child(node);
  }
  var first = child(node, is_text);
  reset(node);
  return first;
}
function sibling(node, count = 1, is_text = false) {
  let next_sibling = hydrating ? hydrate_node : node;
  var last_sibling;
  while (count--) {
    last_sibling = next_sibling;
    next_sibling = /** @type {TemplateNode} */
    /* @__PURE__ */ get_next_sibling(next_sibling);
  }
  if (!hydrating) {
    return next_sibling;
  }
  if (is_text) {
    if (next_sibling?.nodeType !== TEXT_NODE) {
      var text2 = create_text();
      if (next_sibling === null) {
        last_sibling?.after(text2);
      } else {
        next_sibling.before(text2);
      }
      set_hydrate_node(text2);
      return text2;
    }
    merge_text_nodes(
      /** @type {Text} */
      next_sibling
    );
  }
  set_hydrate_node(next_sibling);
  return next_sibling;
}
function clear_text_content(node) {
  node.textContent = "";
}
function should_defer_append() {
  if (!async_mode_flag) return false;
  if (eager_block_effects !== null) return false;
  var flags2 = (
    /** @type {Effect} */
    active_effect.f
  );
  return (flags2 & REACTION_RAN) !== 0;
}
function create_element(tag2, namespace, is2) {
  if (namespace == null || namespace === NAMESPACE_HTML) {
    return (
      /** @type {T extends keyof HTMLElementTagNameMap ? HTMLElementTagNameMap[T] : Element} */
      is2 ? document.createElement(tag2, { is: is2 }) : document.createElement(tag2)
    );
  }
  return (
    /** @type {T extends keyof HTMLElementTagNameMap ? HTMLElementTagNameMap[T] : Element} */
    is2 ? document.createElementNS(namespace, tag2, { is: is2 }) : document.createElementNS(namespace, tag2)
  );
}
function merge_text_nodes(text2) {
  if (
    /** @type {string} */
    text2.nodeValue.length < 65536
  ) {
    return;
  }
  let next2 = text2.nextSibling;
  while (next2 !== null && next2.nodeType === TEXT_NODE) {
    next2.remove();
    text2.nodeValue += /** @type {string} */
    next2.nodeValue;
    next2 = text2.nextSibling;
  }
}

// node_modules/svelte/src/internal/client/error-handling.js
var adjustments = /* @__PURE__ */ new WeakMap();
function handle_error(error) {
  var effect2 = active_effect;
  if (effect2 === null) {
    active_reaction.f |= ERROR_VALUE;
    return error;
  }
  if (dev_fallback_default && error instanceof Error && !adjustments.has(error)) {
    adjustments.set(error, get_adjustments(error, effect2));
  }
  if ((effect2.f & REACTION_RAN) === 0 && (effect2.f & EFFECT) === 0) {
    if (dev_fallback_default && !effect2.parent && error instanceof Error) {
      apply_adjustments(error);
    }
    throw error;
  }
  invoke_error_boundary(error, effect2);
}
function invoke_error_boundary(error, effect2) {
  if (effect2 !== null && (effect2.f & DESTROYED) !== 0) {
    return;
  }
  while (effect2 !== null) {
    if ((effect2.f & BOUNDARY_EFFECT) !== 0 && (effect2.f & (DESTROYED | DESTROYING)) === 0) {
      if ((effect2.f & REACTION_RAN) === 0) {
        throw error;
      }
      try {
        effect2.b.error(error);
        return;
      } catch (e) {
        error = e;
      }
    }
    effect2 = effect2.parent;
  }
  if (dev_fallback_default && error instanceof Error) {
    apply_adjustments(error);
  }
  throw error;
}
function get_adjustments(error, effect2) {
  const message_descriptor = get_descriptor(error, "message");
  if (message_descriptor && !message_descriptor.configurable) return;
  var indent = is_firefox ? "  " : "	";
  var component_stack = `
${indent}in ${effect2.fn?.name || "<unknown>"}`;
  var context = effect2.ctx;
  while (context !== null) {
    component_stack += `
${indent}in ${context.function?.[FILENAME].split("/").pop()}`;
    context = context.p;
  }
  return {
    message: error.message + `
${component_stack}
`,
    stack: error.stack?.split("\n").filter((line) => !line.includes("svelte/src/internal")).join("\n")
  };
}
function apply_adjustments(error) {
  const adjusted = adjustments.get(error);
  if (adjusted) {
    define_property(error, "message", {
      value: adjusted.message
    });
    define_property(error, "stack", {
      value: adjusted.stack
    });
  }
}

// node_modules/svelte/src/internal/client/reactivity/effects.js
function validate_effect(rune) {
  if (active_effect === null) {
    if (active_reaction === null) {
      effect_orphan(rune);
    }
    effect_in_unowned_derived();
  }
  if (is_destroying_effect) {
    effect_in_teardown(rune);
  }
}
function push_effect(effect2, parent_effect) {
  var parent_last = parent_effect.last;
  if (parent_last === null) {
    parent_effect.last = parent_effect.first = effect2;
  } else {
    parent_last.next = effect2;
    effect2.prev = parent_last;
    parent_effect.last = effect2;
  }
}
function create_effect(type, fn) {
  var parent = active_effect;
  if (dev_fallback_default) {
    while (parent !== null && (parent.f & EAGER_EFFECT) !== 0) {
      parent = parent.parent;
    }
  }
  if (parent !== null && (parent.f & INERT) !== 0) {
    type |= INERT;
  }
  var effect2 = {
    ctx: component_context,
    deps: null,
    nodes: null,
    f: type | DIRTY | CONNECTED,
    first: null,
    fn,
    last: null,
    next: null,
    parent,
    b: parent && parent.b,
    prev: null,
    teardown: null,
    wv: 0,
    ac: null
  };
  if (dev_fallback_default) {
    effect2.component_function = dev_current_component_function;
  }
  current_batch?.register_created_effect(effect2);
  var e = effect2;
  if ((type & EFFECT) !== 0) {
    if (collected_effects !== null) {
      collected_effects.push(effect2);
    } else {
      Batch.ensure().schedule(effect2);
    }
  } else if (fn !== null) {
    try {
      update_effect(effect2);
    } catch (e2) {
      destroy_effect(effect2);
      throw e2;
    }
    if (e.deps === null && e.teardown === null && e.nodes === null && e.first === e.last && // either `null`, or a singular child
    (e.f & EFFECT_PRESERVED) === 0) {
      e = e.first;
      if ((type & BLOCK_EFFECT) !== 0 && (type & EFFECT_TRANSPARENT) !== 0 && e !== null) {
        e.f |= EFFECT_TRANSPARENT;
      }
    }
  }
  if (e !== null) {
    e.parent = parent;
    if (parent !== null) {
      push_effect(e, parent);
    }
    if (active_reaction !== null && (active_reaction.f & DERIVED) !== 0 && (type & ROOT_EFFECT) === 0) {
      var derived2 = (
        /** @type {Derived} */
        active_reaction
      );
      (derived2.effects ??= []).push(e);
    }
  }
  return effect2;
}
function effect_tracking() {
  return active_reaction !== null && !untracking;
}
function teardown(fn) {
  const effect2 = create_effect(RENDER_EFFECT, null);
  set_signal_status(effect2, CLEAN);
  effect2.teardown = fn;
  return effect2;
}
function user_effect(fn) {
  validate_effect("$effect");
  if (dev_fallback_default) {
    define_property(fn, "name", {
      value: "$effect"
    });
  }
  var flags2 = (
    /** @type {Effect} */
    active_effect.f
  );
  var defer = !active_reaction && (flags2 & BRANCH_EFFECT) !== 0 && component_context !== null && !component_context.i;
  if (defer) {
    var context = (
      /** @type {ComponentContext} */
      component_context
    );
    (context.e ??= []).push(fn);
  } else {
    return create_user_effect(fn);
  }
}
function create_user_effect(fn) {
  return create_effect(EFFECT | USER_EFFECT, fn);
}
function user_pre_effect(fn) {
  validate_effect("$effect.pre");
  if (dev_fallback_default) {
    define_property(fn, "name", {
      value: "$effect.pre"
    });
  }
  return create_effect(RENDER_EFFECT | USER_EFFECT, fn);
}
function effect_root(fn) {
  Batch.ensure();
  const effect2 = create_effect(ROOT_EFFECT | EFFECT_PRESERVED, fn);
  return () => {
    destroy_effect(effect2);
  };
}
function component_root(fn) {
  Batch.ensure();
  const effect2 = create_effect(ROOT_EFFECT | EFFECT_PRESERVED, fn);
  return (options = {}) => {
    return new Promise((fulfil) => {
      if (options.outro) {
        pause_effect(effect2, () => {
          destroy_effect(effect2);
          fulfil(void 0);
        });
      } else {
        destroy_effect(effect2);
        fulfil(void 0);
      }
    });
  };
}
function effect(fn) {
  return create_effect(EFFECT, fn);
}
function legacy_pre_effect(deps, fn) {
  var context = (
    /** @type {ComponentContextLegacy} */
    component_context
  );
  var token = { effect: null, ran: false, deps };
  context.l.$.push(token);
  token.effect = render_effect(() => {
    deps();
    if (token.ran) return;
    token.ran = true;
    var effect2 = (
      /** @type {Effect} */
      active_effect
    );
    try {
      set_active_effect(effect2.parent);
      untrack(fn);
    } finally {
      set_active_effect(effect2);
    }
  });
}
function legacy_pre_effect_reset() {
  var context = (
    /** @type {ComponentContextLegacy} */
    component_context
  );
  render_effect(() => {
    for (var token of context.l.$) {
      token.deps();
      var effect2 = token.effect;
      if ((effect2.f & CLEAN) !== 0 && effect2.deps !== null) {
        set_signal_status(effect2, MAYBE_DIRTY);
      }
      if (is_dirty(effect2)) {
        update_effect(effect2);
      }
      token.ran = false;
    }
  });
}
function async_effect(fn) {
  return create_effect(ASYNC | EFFECT_PRESERVED, fn);
}
function render_effect(fn, flags2 = 0) {
  return create_effect(RENDER_EFFECT | flags2, fn);
}
function template_effect(fn, sync = [], async2 = [], blockers = []) {
  flatten(blockers, sync, async2, (values) => {
    create_effect(RENDER_EFFECT, () => {
      fn(...values.map(get));
    });
  });
}
function block(fn, flags2 = 0) {
  var effect2 = create_effect(BLOCK_EFFECT | flags2, fn);
  if (dev_fallback_default) {
    effect2.dev_stack = dev_stack;
  }
  return effect2;
}
function branch(fn) {
  return create_effect(BRANCH_EFFECT | EFFECT_PRESERVED, fn);
}
function execute_effect_teardown(effect2) {
  var teardown2 = effect2.teardown;
  if (teardown2 !== null) {
    const previously_destroying_effect = is_destroying_effect;
    const previous_reaction = active_reaction;
    set_is_destroying_effect(true);
    set_active_reaction(null);
    try {
      teardown2.call(null);
    } catch (error) {
      invoke_error_boundary(error, effect2.parent);
    } finally {
      set_is_destroying_effect(previously_destroying_effect);
      set_active_reaction(previous_reaction);
    }
  }
}
function destroy_effect_children(signal, remove_dom = false) {
  var effect2 = signal.first;
  signal.first = signal.last = null;
  while (effect2 !== null) {
    const controller = effect2.ac;
    if (controller !== null) {
      without_reactive_context(() => {
        controller.abort(STALE_REACTION);
      });
    }
    var next2 = effect2.next;
    if ((effect2.f & ROOT_EFFECT) !== 0) {
      effect2.parent = null;
    } else {
      destroy_effect(effect2, remove_dom);
    }
    effect2 = next2;
  }
}
function destroy_block_effect_children(signal) {
  var effect2 = signal.first;
  while (effect2 !== null) {
    var next2 = effect2.next;
    if ((effect2.f & BRANCH_EFFECT) === 0) {
      destroy_effect(effect2);
    }
    effect2 = next2;
  }
}
function destroy_effect(effect2, remove_dom = true) {
  var removed = false;
  if ((remove_dom || (effect2.f & HEAD_EFFECT) !== 0) && effect2.nodes !== null && effect2.nodes.end !== null) {
    remove_effect_dom(
      effect2.nodes.start,
      /** @type {TemplateNode} */
      effect2.nodes.end
    );
    removed = true;
  }
  effect2.f |= DESTROYING;
  destroy_effect_children(effect2, remove_dom && !removed);
  remove_reactions(effect2, 0);
  var transitions = effect2.nodes && effect2.nodes.t;
  if (transitions !== null) {
    for (const transition2 of transitions) {
      transition2.stop();
    }
  }
  execute_effect_teardown(effect2);
  effect2.f ^= DESTROYING;
  effect2.f |= DESTROYED;
  var parent = effect2.parent;
  if (parent !== null && parent.first !== null) {
    unlink_effect(effect2);
  }
  if (dev_fallback_default) {
    effect2.component_function = null;
  }
  effect2.next = effect2.prev = effect2.teardown = effect2.ctx = effect2.deps = effect2.fn = effect2.nodes = effect2.ac = effect2.b = null;
}
function remove_effect_dom(node, end) {
  while (node !== null) {
    var next2 = node === end ? null : get_next_sibling(node);
    node.remove();
    node = next2;
  }
}
function unlink_effect(effect2) {
  var parent = effect2.parent;
  var prev = effect2.prev;
  var next2 = effect2.next;
  if (prev !== null) prev.next = next2;
  if (next2 !== null) next2.prev = prev;
  if (parent !== null) {
    if (parent.first === effect2) parent.first = next2;
    if (parent.last === effect2) parent.last = prev;
  }
}
function pause_effect(effect2, callback, destroy = true) {
  var transitions = [];
  effect2.f |= PAUSED;
  pause_children(effect2, transitions, true);
  var fn = () => {
    if (destroy) destroy_effect(effect2);
    if (callback) callback();
  };
  var remaining = transitions.length;
  if (remaining > 0) {
    var check = () => --remaining || fn();
    for (var transition2 of transitions) {
      transition2.out(check);
    }
  } else {
    fn();
  }
}
function pause_children(effect2, transitions, local) {
  if ((effect2.f & INERT) !== 0) return;
  effect2.f ^= INERT;
  var t = effect2.nodes && effect2.nodes.t;
  if (t !== null) {
    for (const transition2 of t) {
      if (transition2.is_global || local) {
        transitions.push(transition2);
      }
    }
  }
  var child2 = effect2.first;
  while (child2 !== null) {
    var sibling2 = child2.next;
    if ((child2.f & ROOT_EFFECT) === 0) {
      var transparent = (child2.f & EFFECT_TRANSPARENT) !== 0 || // If this is a branch effect without a block effect parent,
      // it means the parent block effect was pruned. In that case,
      // transparency information was transferred to the branch effect.
      (child2.f & BRANCH_EFFECT) !== 0 && (effect2.f & BLOCK_EFFECT) !== 0;
      pause_children(child2, transitions, transparent ? local : false);
    }
    child2 = sibling2;
  }
}
function resume_effect(effect2) {
  effect2.f &= ~PAUSED;
  resume_children(effect2, true);
}
function resume_children(effect2, local) {
  if ((effect2.f & PAUSED) !== 0) return;
  if ((effect2.f & INERT) === 0) return;
  effect2.f ^= INERT;
  if ((effect2.f & CLEAN) === 0) {
    set_signal_status(effect2, DIRTY);
    Batch.ensure().schedule(effect2);
  }
  var child2 = effect2.first;
  while (child2 !== null) {
    var sibling2 = child2.next;
    var transparent = (child2.f & EFFECT_TRANSPARENT) !== 0 || (child2.f & BRANCH_EFFECT) !== 0;
    resume_children(child2, transparent ? local : false);
    child2 = sibling2;
  }
  var t = effect2.nodes && effect2.nodes.t;
  if (t !== null) {
    for (const transition2 of t) {
      if (transition2.is_global || local) {
        transition2.in();
      }
    }
  }
}
function move_effect(effect2, fragment) {
  if (!effect2.nodes) return;
  var node = effect2.nodes.start;
  var end = effect2.nodes.end;
  while (node !== null) {
    var next2 = node === end ? null : get_next_sibling(node);
    fragment.append(node);
    node = next2;
  }
}

// node_modules/svelte/src/internal/client/legacy.js
var captured_signals = null;

// node_modules/svelte/src/internal/client/runtime.js
var is_updating_effect = false;
var is_destroying_effect = false;
function set_is_destroying_effect(value) {
  is_destroying_effect = value;
}
var active_reaction = null;
var untracking = false;
function set_active_reaction(reaction) {
  active_reaction = reaction;
}
var active_effect = null;
function set_active_effect(effect2) {
  active_effect = effect2;
}
var current_sources = null;
function push_reaction_value(value) {
  if (active_reaction !== null && (!async_mode_flag && (active_reaction.f & REACTION_IS_UPDATING) !== 0 || (active_reaction.f & DERIVED) !== 0)) {
    (current_sources ??= /* @__PURE__ */ new Set()).add(value);
  }
}
var new_deps = null;
var skipped_deps = 0;
var untracked_writes = null;
function set_untracked_writes(value) {
  untracked_writes = value;
}
var write_version = 1;
var read_version = 0;
var update_version = read_version;
function set_update_version(value) {
  update_version = value;
}
function increment_write_version() {
  return ++write_version;
}
function is_dirty(reaction) {
  var flags2 = reaction.f;
  if ((flags2 & DIRTY) !== 0) {
    return true;
  }
  if ((flags2 & MAYBE_DIRTY) !== 0) {
    var dependencies = (
      /** @type {Value[]} */
      reaction.deps
    );
    var length = dependencies.length;
    for (var i = 0; i < length; i++) {
      var dependency = dependencies[i];
      if (is_dirty(
        /** @type {Derived} */
        dependency
      )) {
        update_derived(
          /** @type {Derived} */
          dependency
        );
      }
      if (dependency.wv > reaction.wv) {
        return true;
      }
    }
    if ((flags2 & CONNECTED) !== 0 && // During time traveling we don't want to reset the status so that
    // traversal of the graph in the other batches still happens
    batch_values === null) {
      set_signal_status(reaction, CLEAN);
    }
  }
  return false;
}
function schedule_possible_effect_self_invalidation(signal, effect2, root6 = true) {
  var reactions = signal.reactions;
  if (reactions === null) return;
  if (!async_mode_flag && current_sources !== null && current_sources.has(signal)) {
    return;
  }
  for (var i = 0; i < reactions.length; i++) {
    var reaction = reactions[i];
    if ((reaction.f & DERIVED) !== 0) {
      schedule_possible_effect_self_invalidation(
        /** @type {Derived} */
        reaction,
        effect2,
        false
      );
    } else if (effect2 === reaction) {
      if (root6) {
        set_signal_status(reaction, DIRTY);
      } else if ((reaction.f & CLEAN) !== 0) {
        set_signal_status(reaction, MAYBE_DIRTY);
      }
      schedule_effect(
        /** @type {Effect} */
        reaction
      );
    }
  }
}
function update_reaction(reaction) {
  var previous_deps = new_deps;
  var previous_skipped_deps = skipped_deps;
  var previous_untracked_writes = untracked_writes;
  var previous_reaction = active_reaction;
  var previous_sources = current_sources;
  var previous_component_context = component_context;
  var previous_untracking = untracking;
  var previous_update_version = update_version;
  var flags2 = reaction.f;
  new_deps = /** @type {null | Value[]} */
  null;
  skipped_deps = 0;
  untracked_writes = null;
  active_reaction = (flags2 & (BRANCH_EFFECT | ROOT_EFFECT)) === 0 ? reaction : null;
  current_sources = null;
  set_component_context(reaction.ctx);
  untracking = false;
  update_version = ++read_version;
  if (reaction.ac !== null) {
    without_reactive_context(() => {
      reaction.ac.abort(STALE_REACTION);
    });
    reaction.ac = null;
  }
  try {
    reaction.f |= REACTION_IS_UPDATING;
    var fn = (
      /** @type {Function} */
      reaction.fn
    );
    var result = fn();
    reaction.f |= REACTION_RAN;
    var deps = update_dependencies(reaction);
    if (is_runes() && untracked_writes !== null && !untracking && deps !== null && (reaction.f & (DERIVED | MAYBE_DIRTY | DIRTY)) === 0) {
      for (var i = 0; i < /** @type {Source[]} */
      untracked_writes.length; i++) {
        schedule_possible_effect_self_invalidation(
          untracked_writes[i],
          /** @type {Effect} */
          reaction
        );
      }
    }
    if (previous_reaction !== null && previous_reaction !== reaction) {
      read_version++;
      if (previous_reaction.deps !== null) {
        for (let i2 = 0; i2 < previous_skipped_deps; i2 += 1) {
          previous_reaction.deps[i2].rv = read_version;
        }
      }
      if (previous_deps !== null) {
        for (const dep of previous_deps) {
          dep.rv = read_version;
        }
      }
      if (untracked_writes !== null) {
        if (previous_untracked_writes === null) {
          previous_untracked_writes = untracked_writes;
        } else {
          previous_untracked_writes.push(.../** @type {Source[]} */
          untracked_writes);
        }
      }
    }
    if ((reaction.f & ERROR_VALUE) !== 0) {
      reaction.f ^= ERROR_VALUE;
    }
    return result;
  } catch (error) {
    update_dependencies(reaction);
    return handle_error(error);
  } finally {
    reaction.f ^= REACTION_IS_UPDATING;
    new_deps = previous_deps;
    skipped_deps = previous_skipped_deps;
    untracked_writes = previous_untracked_writes;
    active_reaction = previous_reaction;
    current_sources = previous_sources;
    set_component_context(previous_component_context);
    untracking = previous_untracking;
    update_version = previous_update_version;
  }
}
function update_dependencies(reaction) {
  var deps = reaction.deps;
  var is_fork = current_batch?.is_fork;
  if (new_deps !== null) {
    var i;
    if (!is_fork) {
      remove_reactions(reaction, skipped_deps);
    }
    if (deps !== null && skipped_deps > 0) {
      deps.length = skipped_deps + new_deps.length;
      for (i = 0; i < new_deps.length; i++) {
        deps[skipped_deps + i] = new_deps[i];
      }
    } else {
      reaction.deps = deps = new_deps;
    }
    if (effect_tracking() && (reaction.f & CONNECTED) !== 0) {
      for (i = skipped_deps; i < deps.length; i++) {
        (deps[i].reactions ??= []).push(reaction);
      }
    }
  } else if (!is_fork && deps !== null && skipped_deps < deps.length) {
    remove_reactions(reaction, skipped_deps);
    deps.length = skipped_deps;
  }
  return deps;
}
function remove_reaction(signal, dependency) {
  let reactions = dependency.reactions;
  if (reactions !== null) {
    var index2 = index_of.call(reactions, signal);
    if (index2 !== -1) {
      var new_length = reactions.length - 1;
      if (new_length === 0) {
        reactions = dependency.reactions = null;
      } else {
        reactions[index2] = reactions[new_length];
        reactions.pop();
      }
    }
  }
  if (reactions === null && (dependency.f & DERIVED) !== 0 && // Destroying a child effect while updating a parent effect can cause a dependency to appear
  // to be unused, when in fact it is used by the currently-updating parent. Checking `new_deps`
  // allows us to skip the expensive work of disconnecting and immediately reconnecting it
  (new_deps === null || !includes.call(new_deps, dependency))) {
    var derived2 = (
      /** @type {Derived} */
      dependency
    );
    if ((derived2.f & CONNECTED) !== 0) {
      derived2.f ^= CONNECTED;
    }
    if (derived2.v !== UNINITIALIZED) {
      update_derived_status(derived2);
    }
    if (derived2.ac !== null) {
      without_reactive_context(() => {
        derived2.ac.abort(STALE_REACTION);
        derived2.ac = null;
        set_signal_status(derived2, DIRTY);
      });
    }
    freeze_derived_effects(derived2);
    remove_reactions(derived2, 0);
  }
}
function remove_reactions(signal, start_index) {
  var dependencies = signal.deps;
  if (dependencies === null) return;
  for (var i = start_index; i < dependencies.length; i++) {
    remove_reaction(signal, dependencies[i]);
  }
}
function update_effect(effect2) {
  var flags2 = effect2.f;
  if ((flags2 & DESTROYED) !== 0) {
    return;
  }
  set_signal_status(effect2, CLEAN);
  var previous_effect = active_effect;
  var was_updating_effect = is_updating_effect;
  active_effect = effect2;
  is_updating_effect = (flags2 & (BRANCH_EFFECT | ROOT_EFFECT)) === 0;
  if (dev_fallback_default) {
    var previous_component_fn = dev_current_component_function;
    set_dev_current_component_function(effect2.component_function);
    var previous_stack = (
      /** @type {any} */
      dev_stack
    );
    set_dev_stack(effect2.dev_stack ?? dev_stack);
  }
  try {
    if ((flags2 & (BLOCK_EFFECT | MANAGED_EFFECT)) !== 0) {
      destroy_block_effect_children(effect2);
    } else {
      destroy_effect_children(effect2);
    }
    execute_effect_teardown(effect2);
    var teardown2 = update_reaction(effect2);
    effect2.teardown = typeof teardown2 === "function" ? teardown2 : null;
    effect2.wv = write_version;
    if (dev_fallback_default && tracing_mode_flag && (effect2.f & DIRTY) !== 0 && effect2.deps !== null) {
      for (var dep of effect2.deps) {
        if (dep.set_during_effect) {
          dep.wv = increment_write_version();
          dep.set_during_effect = false;
        }
      }
    }
  } finally {
    is_updating_effect = was_updating_effect;
    active_effect = previous_effect;
    if (dev_fallback_default) {
      set_dev_current_component_function(previous_component_fn);
      set_dev_stack(previous_stack);
    }
  }
}
async function tick() {
  if (async_mode_flag) {
    return new Promise((f) => {
      requestAnimationFrame(() => f());
      setTimeout(() => f());
    });
  }
  await Promise.resolve();
  flushSync();
}
function get(signal) {
  var flags2 = signal.f;
  var is_derived = (flags2 & DERIVED) !== 0;
  captured_signals?.add(signal);
  if (active_reaction !== null && !untracking) {
    var destroyed = active_effect !== null && (active_effect.f & DESTROYED) !== 0;
    if (!destroyed && (current_sources === null || !current_sources.has(signal))) {
      var deps = active_reaction.deps;
      if ((active_reaction.f & REACTION_IS_UPDATING) !== 0) {
        if (signal.rv < read_version) {
          signal.rv = read_version;
          if (new_deps === null && deps !== null && deps[skipped_deps] === signal) {
            skipped_deps++;
          } else if (new_deps === null) {
            new_deps = [signal];
          } else {
            new_deps.push(signal);
          }
        }
      } else {
        active_reaction.deps ??= [];
        if (!includes.call(active_reaction.deps, signal)) {
          active_reaction.deps.push(signal);
        }
        var reactions = signal.reactions;
        if (reactions === null) {
          signal.reactions = [active_reaction];
        } else if (!includes.call(reactions, active_reaction)) {
          reactions.push(active_reaction);
        }
      }
    }
  }
  if (dev_fallback_default) {
    if (!untracking && reactivity_loss_tracker && // By checking that current/previous batch are null we filter out false positives.
    // reactivity_loss_tracker is only reset after a microtask, so if a flush happens
    // before that, we get warnings for things we shouldn't warn on.
    current_batch === null && previous_batch === null && !reactivity_loss_tracker.warned && (reactivity_loss_tracker.effect.f & REACTION_IS_UPDATING) === 0 && !reactivity_loss_tracker.effect_deps.has(signal)) {
      reactivity_loss_tracker.warned = true;
      await_reactivity_loss(
        /** @type {string} */
        signal.label
      );
      var trace2 = get_error("traced at");
      if (trace2) console.warn(trace2);
    }
    recent_async_deriveds.delete(signal);
    if (tracing_mode_flag && !untracking && tracing_expressions !== null && active_reaction !== null && tracing_expressions.reaction === active_reaction) {
      if (signal.trace) {
        signal.trace();
      } else {
        trace2 = get_error("traced at");
        if (trace2) {
          var entry = tracing_expressions.entries.get(signal);
          if (entry === void 0) {
            entry = { traces: [] };
            tracing_expressions.entries.set(signal, entry);
          }
          var last = entry.traces[entry.traces.length - 1];
          if (trace2.stack !== last?.stack) {
            entry.traces.push(trace2);
          }
        }
      }
    }
  }
  if (is_destroying_effect && old_values.has(signal)) {
    return old_values.get(signal);
  }
  if (is_derived) {
    var derived2 = (
      /** @type {Derived} */
      signal
    );
    if (is_destroying_effect) {
      var value = derived2.v;
      if ((derived2.f & CLEAN) === 0 && derived2.reactions !== null || depends_on_old_values(derived2)) {
        value = execute_derived(derived2);
      }
      old_values.set(derived2, value);
      return value;
    }
    var should_connect = (derived2.f & CONNECTED) === 0 && !untracking && active_reaction !== null && (is_updating_effect || (active_reaction.f & CONNECTED) !== 0);
    var is_new = (derived2.f & REACTION_RAN) === 0;
    if (is_dirty(derived2)) {
      if (should_connect) {
        derived2.f |= CONNECTED;
      }
      update_derived(derived2);
    }
    if (should_connect && !is_new) {
      unfreeze_derived_effects(derived2);
      reconnect(derived2);
    }
  }
  if (batch_values?.has(signal)) {
    return batch_values.get(signal);
  }
  if ((signal.f & ERROR_VALUE) !== 0) {
    throw signal.v;
  }
  return signal.v;
}
function reconnect(derived2) {
  derived2.f |= CONNECTED;
  if (derived2.deps === null) return;
  for (const dep of derived2.deps) {
    (dep.reactions ??= []).push(derived2);
    if ((dep.f & DERIVED) !== 0 && (dep.f & CONNECTED) === 0) {
      unfreeze_derived_effects(
        /** @type {Derived} */
        dep
      );
      reconnect(
        /** @type {Derived} */
        dep
      );
    }
  }
}
function depends_on_old_values(derived2) {
  if (derived2.v === UNINITIALIZED) return true;
  if (derived2.deps === null) return false;
  for (const dep of derived2.deps) {
    if (old_values.has(dep)) {
      return true;
    }
    if ((dep.f & DERIVED) !== 0 && depends_on_old_values(
      /** @type {Derived} */
      dep
    )) {
      return true;
    }
  }
  return false;
}
function untrack(fn) {
  var previous_untracking = untracking;
  try {
    untracking = true;
    return fn();
  } finally {
    untracking = previous_untracking;
  }
}
function deep_read_state(value) {
  if (typeof value !== "object" || !value || value instanceof EventTarget) {
    return;
  }
  if (STATE_SYMBOL in value) {
    deep_read(value);
  } else if (!Array.isArray(value)) {
    for (let key2 in value) {
      const prop2 = value[key2];
      if (typeof prop2 === "object" && prop2 && STATE_SYMBOL in prop2) {
        deep_read(prop2);
      }
    }
  }
}
function deep_read(value, visited = /* @__PURE__ */ new Set()) {
  if (typeof value === "object" && value !== null && // We don't want to traverse DOM elements
  !(value instanceof EventTarget) && !visited.has(value)) {
    visited.add(value);
    if (value instanceof Date) {
      value.getTime();
    }
    for (let key2 in value) {
      try {
        deep_read(value[key2], visited);
      } catch (e) {
      }
    }
    const proto = get_prototype_of(value);
    if (proto !== Object.prototype && proto !== Array.prototype && proto !== Map.prototype && proto !== Set.prototype && proto !== Date.prototype) {
      const descriptors = get_descriptors(proto);
      for (let key2 in descriptors) {
        const get3 = descriptors[key2].get;
        if (get3) {
          try {
            get3.call(value);
          } catch (e) {
          }
        }
      }
    }
  }
}

// node_modules/svelte/src/utils.js
var DOM_BOOLEAN_ATTRIBUTES = [
  "allowfullscreen",
  "async",
  "autofocus",
  "autoplay",
  "checked",
  "controls",
  "default",
  "disabled",
  "formnovalidate",
  "indeterminate",
  "inert",
  "ismap",
  "loop",
  "multiple",
  "muted",
  "nomodule",
  "novalidate",
  "open",
  "playsinline",
  "readonly",
  "required",
  "reversed",
  "seamless",
  "selected",
  "webkitdirectory",
  "defer",
  "disablepictureinpicture",
  "disableremoteplayback"
];
var DOM_PROPERTIES = [
  ...DOM_BOOLEAN_ATTRIBUTES,
  "formNoValidate",
  "isMap",
  "noModule",
  "playsInline",
  "readOnly",
  "value",
  "volume",
  "defaultValue",
  "defaultChecked",
  "srcObject",
  "noValidate",
  "allowFullscreen",
  "disablePictureInPicture",
  "disableRemotePlayback"
];
var PASSIVE_EVENTS = ["touchstart", "touchmove"];
function is_passive_event(name) {
  return PASSIVE_EVENTS.includes(name);
}
var STATE_CREATION_RUNES = (
  /** @type {const} */
  [
    "$state",
    "$state.raw",
    "$derived",
    "$derived.by"
  ]
);
var RUNES = (
  /** @type {const} */
  [
    ...STATE_CREATION_RUNES,
    "$state.eager",
    "$state.snapshot",
    "$props",
    "$props.id",
    "$bindable",
    "$effect",
    "$effect.pre",
    "$effect.tracking",
    "$effect.root",
    "$effect.pending",
    "$inspect",
    "$inspect().with",
    "$inspect.trace",
    "$host"
  ]
);

// node_modules/svelte/src/internal/client/dom/elements/events.js
var event_symbol = Symbol("events");
var all_registered_events = /* @__PURE__ */ new Set();
var root_event_handles = /* @__PURE__ */ new Set();
function create_event(event_name, dom, handler, options = {}) {
  function target_handler(event2) {
    if (!options.capture) {
      handle_event_propagation.call(dom, event2);
    }
    if (!event2.cancelBubble) {
      return without_reactive_context(() => {
        return handler?.call(this, event2);
      });
    }
  }
  if (event_name.startsWith("pointer") || event_name.startsWith("touch") || event_name === "wheel") {
    target_handler.__removed = false;
    queue_micro_task(() => {
      if (!target_handler.__removed) {
        dom.addEventListener(event_name, target_handler, options);
      }
    });
  } else {
    dom.addEventListener(event_name, target_handler, options);
  }
  return target_handler;
}
function event(event_name, dom, handler, capture2, passive2) {
  var options = { capture: capture2, passive: passive2 };
  var target_handler = create_event(event_name, dom, handler, options);
  if (dom === document.body || // @ts-ignore
  dom === window || // @ts-ignore
  dom === document || // Firefox has quirky behavior, it can happen that we still get "canplay" events when the element is already removed
  dom instanceof HTMLMediaElement) {
    teardown(() => {
      target_handler.__removed = true;
      dom.removeEventListener(event_name, target_handler, options);
    });
  }
}
var last_propagated_event = null;
var last_propagated_event_clear_scheduled = false;
function handle_event_propagation(event2) {
  var handler_element = this;
  var owner_document = (
    /** @type {Node} */
    handler_element.ownerDocument
  );
  var event_name = event2.type;
  var path = event2.composedPath?.() || [];
  var current_target = (
    /** @type {null | Element} */
    path[0] || event2.target
  );
  last_propagated_event = event2;
  if (!last_propagated_event_clear_scheduled) {
    last_propagated_event_clear_scheduled = true;
    setTimeout(() => {
      last_propagated_event_clear_scheduled = false;
      last_propagated_event = null;
    });
  }
  var path_idx = 0;
  var handled_at = last_propagated_event === event2 && event2[event_symbol];
  if (handled_at) {
    var at_idx = path.indexOf(handled_at);
    if (at_idx !== -1 && (handler_element === document || handler_element === /** @type {any} */
    window)) {
      event2[event_symbol] = handler_element;
      return;
    }
    var handler_idx = path.indexOf(handler_element);
    if (handler_idx === -1) {
      return;
    }
    if (at_idx <= handler_idx) {
      path_idx = at_idx;
    }
  }
  current_target = /** @type {Element} */
  path[path_idx] || event2.target;
  if (current_target === handler_element) return;
  define_property(event2, "currentTarget", {
    configurable: true,
    get() {
      return current_target || owner_document;
    }
  });
  var previous_reaction = active_reaction;
  var previous_effect = active_effect;
  set_active_reaction(null);
  set_active_effect(null);
  try {
    var throw_error;
    var other_errors = [];
    while (current_target !== null) {
      if (current_target === handler_element) break;
      try {
        var delegated2 = current_target[event_symbol]?.[event_name];
        if (delegated2 != null && (!/** @type {any} */
        current_target.disabled || // DOM could've been updated already by the time this is reached, so we check this as well
        // -> the target could not have been disabled because it emits the event in the first place
        event2.target === current_target)) {
          delegated2.call(current_target, event2);
        }
      } catch (error) {
        if (throw_error) {
          other_errors.push(error);
        } else {
          throw_error = error;
        }
      }
      if (event2.cancelBubble) break;
      path_idx++;
      current_target = path_idx < path.length ? (
        /** @type {Element} */
        path[path_idx]
      ) : null;
    }
    if (throw_error) {
      for (let error of other_errors) {
        queueMicrotask(() => {
          throw error;
        });
      }
      throw throw_error;
    }
  } finally {
    event2[event_symbol] = handler_element;
    delete event2.currentTarget;
    set_active_reaction(previous_reaction);
    set_active_effect(previous_effect);
  }
}

// node_modules/svelte/src/internal/client/dom/reconciler.js
var policy = (
  // We gotta write it like this because after downleveling the pure comment may end up in the wrong location
  globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", {
    /** @param {string} html */
    createHTML: (html2) => {
      return html2;
    }
  })
);
function create_trusted_html(html2) {
  return (
    /** @type {string} */
    policy?.createHTML(html2) ?? html2
  );
}
function create_fragment_from_html(html2) {
  var elem = create_element("template");
  elem.innerHTML = create_trusted_html(html2.replaceAll("<!>", "<!---->"));
  return elem.content;
}

// node_modules/svelte/src/internal/client/dom/template.js
function assign_nodes(start, end) {
  var effect2 = (
    /** @type {Effect} */
    active_effect
  );
  if (effect2.nodes === null) {
    effect2.nodes = { start, end, a: null, t: null };
  }
}
// @__NO_SIDE_EFFECTS__
function from_html(content, flags2) {
  var is_fragment = (flags2 & TEMPLATE_FRAGMENT) !== 0;
  var use_import_node = (flags2 & TEMPLATE_USE_IMPORT_NODE) !== 0;
  var node;
  var has_start = !content.startsWith("<!>");
  return () => {
    if (hydrating) {
      assign_nodes(hydrate_node, null);
      return hydrate_node;
    }
    if (node === void 0) {
      node = create_fragment_from_html(has_start ? content : "<!>" + content);
      if (!is_fragment) node = /** @type {TemplateNode} */
      get_first_child(node);
    }
    var clone = (
      /** @type {TemplateNode} */
      use_import_node || is_firefox ? document.importNode(node, true) : node.cloneNode(true)
    );
    if (is_fragment) {
      var start = (
        /** @type {TemplateNode} */
        get_first_child(clone)
      );
      var end = (
        /** @type {TemplateNode} */
        clone.lastChild
      );
      assign_nodes(start, end);
    } else {
      assign_nodes(clone, clone);
    }
    return clone;
  };
}
// @__NO_SIDE_EFFECTS__
function from_namespace(content, flags2, ns = "svg") {
  var has_start = !content.startsWith("<!>");
  var is_fragment = (flags2 & TEMPLATE_FRAGMENT) !== 0;
  var wrapped = `<${ns}>${has_start ? content : "<!>" + content}</${ns}>`;
  var node;
  return () => {
    if (hydrating) {
      assign_nodes(hydrate_node, null);
      return hydrate_node;
    }
    if (!node) {
      var fragment = (
        /** @type {DocumentFragment} */
        create_fragment_from_html(wrapped)
      );
      var root6 = (
        /** @type {Element} */
        get_first_child(fragment)
      );
      if (is_fragment) {
        node = document.createDocumentFragment();
        while (get_first_child(root6)) {
          node.appendChild(
            /** @type {TemplateNode} */
            get_first_child(root6)
          );
        }
      } else {
        node = /** @type {Element} */
        get_first_child(root6);
      }
    }
    var clone = (
      /** @type {TemplateNode} */
      node.cloneNode(true)
    );
    if (is_fragment) {
      var start = (
        /** @type {TemplateNode} */
        get_first_child(clone)
      );
      var end = (
        /** @type {TemplateNode} */
        clone.lastChild
      );
      assign_nodes(start, end);
    } else {
      assign_nodes(clone, clone);
    }
    return clone;
  };
}
// @__NO_SIDE_EFFECTS__
function from_svg(content, flags2) {
  return /* @__PURE__ */ from_namespace(content, flags2, "svg");
}
function text(value = "") {
  if (!hydrating) {
    var t = create_text(value + "");
    assign_nodes(t, t);
    return t;
  }
  var node = hydrate_node;
  if (node.nodeType !== TEXT_NODE) {
    node.before(node = create_text());
    set_hydrate_node(node);
  } else {
    merge_text_nodes(
      /** @type {Text} */
      node
    );
  }
  assign_nodes(node, node);
  return node;
}
function comment() {
  if (hydrating) {
    assign_nodes(hydrate_node, null);
    return hydrate_node;
  }
  var frag = document.createDocumentFragment();
  var start = document.createComment("");
  var anchor = create_text();
  frag.append(start, anchor);
  assign_nodes(start, anchor);
  return frag;
}
function append(anchor, dom) {
  if (hydrating) {
    var effect2 = (
      /** @type {Effect & { nodes: EffectNodes }} */
      active_effect
    );
    if ((effect2.f & REACTION_RAN) === 0 || effect2.nodes.end === null) {
      effect2.nodes.end = hydrate_node;
    }
    hydrate_next();
    return;
  }
  if (anchor === null) {
    return;
  }
  anchor.before(
    /** @type {Node} */
    dom
  );
}

// node_modules/svelte/src/reactivity/create-subscriber.js
function createSubscriber(start) {
  let subscribers = 0;
  let version = source(0);
  let stop;
  if (dev_fallback_default) {
    tag(version, "createSubscriber version");
  }
  return () => {
    if (effect_tracking()) {
      get(version);
      render_effect(() => {
        if (subscribers === 0) {
          stop = untrack(() => start(() => increment(version)));
        }
        subscribers += 1;
        return () => {
          queue_micro_task(() => {
            subscribers -= 1;
            if (subscribers === 0) {
              stop?.();
              stop = void 0;
              increment(version);
            }
          });
        };
      });
    }
  };
}

// node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var flags = EFFECT_TRANSPARENT | EFFECT_PRESERVED;
function boundary(node, props, children, transform_error) {
  new Boundary(node, props, children, transform_error);
}
var Boundary = class {
  /** @type {Boundary | null} */
  parent;
  is_pending = false;
  /**
   * API-level transformError transform function. Transforms errors before they reach the `failed` snippet.
   * Inherited from parent boundary, or defaults to identity.
   * @type {(error: unknown) => unknown}
   */
  transform_error;
  /** @type {TemplateNode} */
  #anchor;
  /** @type {TemplateNode | null} */
  #hydrate_open = hydrating ? hydrate_node : null;
  /** @type {BoundaryProps} */
  #props;
  /** @type {((anchor: Node) => void)} */
  #children;
  /** @type {Effect} */
  #effect;
  /** @type {Effect | null} */
  #main_effect = null;
  /** @type {Effect | null} */
  #pending_effect = null;
  /** @type {Effect | null} */
  #failed_effect = null;
  /** @type {DocumentFragment | null} */
  #offscreen_fragment = null;
  #local_pending_count = 0;
  #pending_count = 0;
  #pending_count_update_queued = false;
  /** @type {Set<Effect>} */
  #dirty_effects = /* @__PURE__ */ new Set();
  /** @type {Set<Effect>} */
  #maybe_dirty_effects = /* @__PURE__ */ new Set();
  /**
   * A source containing the number of pending async deriveds/expressions.
   * Only created if `$effect.pending()` is used inside the boundary,
   * otherwise updating the source results in needless `Batch.ensure()`
   * calls followed by no-op flushes
   * @type {Source<number> | null}
   */
  #effect_pending = null;
  #effect_pending_subscriber = createSubscriber(() => {
    this.#effect_pending = source(this.#local_pending_count);
    if (dev_fallback_default) {
      tag(this.#effect_pending, "$effect.pending()");
    }
    return () => {
      this.#effect_pending = null;
    };
  });
  /**
   * @param {TemplateNode} node
   * @param {BoundaryProps} props
   * @param {((anchor: Node) => void)} children
   * @param {((error: unknown) => unknown) | undefined} [transform_error]
   */
  constructor(node, props, children, transform_error) {
    this.#anchor = node;
    this.#props = props;
    this.#children = (anchor) => {
      var effect2 = (
        /** @type {Effect} */
        active_effect
      );
      effect2.b = this;
      effect2.f |= BOUNDARY_EFFECT;
      children(anchor);
    };
    this.parent = /** @type {Effect} */
    active_effect.b;
    this.transform_error = transform_error ?? this.parent?.transform_error ?? ((e) => e);
    this.#effect = block(() => {
      if (hydrating) {
        const comment2 = (
          /** @type {Comment} */
          this.#hydrate_open
        );
        hydrate_next();
        const server_rendered_pending = comment2.data === HYDRATION_START_ELSE;
        const server_rendered_failed = comment2.data.startsWith(HYDRATION_START_FAILED);
        if (server_rendered_failed) {
          const serialized_error = JSON.parse(comment2.data.slice(HYDRATION_START_FAILED.length));
          this.#hydrate_failed_content(serialized_error);
        } else if (server_rendered_pending) {
          this.#hydrate_pending_content();
        } else {
          this.#hydrate_resolved_content();
        }
      } else {
        this.#render();
      }
    }, flags);
    if (hydrating) {
      this.#anchor = hydrate_node;
    }
  }
  #hydrate_resolved_content() {
    try {
      this.#main_effect = branch(() => this.#children(this.#anchor));
    } catch (error) {
      this.error(error);
    }
  }
  /**
   * @param {unknown} error The deserialized error from the server's hydration comment
   */
  #hydrate_failed_content(error) {
    const failed = this.#props.failed;
    const { reset: reset2, invoke_onerror } = this.#create_reset(error);
    queue_micro_task(invoke_onerror);
    if (!failed) return;
    this.#failed_effect = branch(() => {
      failed(
        this.#anchor,
        () => error,
        () => reset2
      );
    });
  }
  /**
   * Creates the `reset` function for a failed boundary, along with a function
   * that invokes `onerror` with it (if provided)
   * @param {unknown} error
   * @returns {{ reset: () => void, invoke_onerror: () => void }}
   */
  #create_reset(error) {
    var did_reset = false;
    var calling_on_error = false;
    const reset2 = () => {
      if (did_reset) {
        svelte_boundary_reset_noop();
        return;
      }
      did_reset = true;
      if (calling_on_error) {
        svelte_boundary_reset_onerror();
      }
      if (this.#failed_effect !== null) {
        pause_effect(this.#failed_effect, () => {
          this.#failed_effect = null;
        });
      }
      this.#run(() => {
        this.#render();
      });
    };
    const invoke_onerror = () => {
      try {
        calling_on_error = true;
        this.#props.onerror?.(error, reset2);
        calling_on_error = false;
      } catch (err) {
        invoke_error_boundary(err, this.#effect && this.#effect.parent);
      }
    };
    return { reset: reset2, invoke_onerror };
  }
  #hydrate_pending_content() {
    const pending2 = this.#props.pending;
    if (!pending2) return;
    this.is_pending = true;
    this.#pending_effect = branch(() => pending2(this.#anchor));
    queue_micro_task(() => {
      var fragment = this.#offscreen_fragment = document.createDocumentFragment();
      var anchor = create_text();
      var handled = false;
      fragment.append(anchor);
      this.#main_effect = this.#run(() => {
        try {
          return branch(() => this.#children(anchor));
        } catch (error) {
          try {
            this.error(error);
            handled = true;
          } catch (error2) {
            invoke_error_boundary(error2, this.#effect.parent);
          }
          return null;
        }
      });
      if (this.#main_effect === null) {
        this.#offscreen_fragment = null;
        if (handled) this.#resolve(
          /** @type {Batch} */
          current_batch
        );
        return;
      }
      if (this.#pending_count === 0) {
        this.#anchor.before(fragment);
        this.#offscreen_fragment = null;
        pause_effect(
          /** @type {Effect} */
          this.#pending_effect,
          () => {
            this.#pending_effect = null;
          }
        );
        this.#resolve(
          /** @type {Batch} */
          current_batch
        );
      }
    });
  }
  #render() {
    try {
      this.is_pending = this.has_pending_snippet();
      this.#pending_count = 0;
      this.#local_pending_count = 0;
      this.#main_effect = branch(() => {
        this.#children(this.#anchor);
      });
      if (this.#pending_count > 0) {
        var fragment = this.#offscreen_fragment = document.createDocumentFragment();
        move_effect(this.#main_effect, fragment);
        const pending2 = (
          /** @type {(anchor: Node) => void} */
          this.#props.pending
        );
        this.#pending_effect = branch(() => pending2(this.#anchor));
      } else {
        this.#resolve(
          /** @type {Batch} */
          current_batch
        );
      }
    } catch (error) {
      this.error(error);
    }
  }
  /**
   * @param {Batch} batch
   */
  #resolve(batch) {
    this.is_pending = false;
    batch.transfer_effects(this.#dirty_effects, this.#maybe_dirty_effects);
  }
  /**
   * Defer an effect inside a pending boundary until the boundary resolves
   * @param {Effect} effect
   */
  defer_effect(effect2) {
    defer_effect(effect2, this.#dirty_effects, this.#maybe_dirty_effects);
  }
  /**
   * Returns `false` if the effect exists inside a boundary whose pending snippet is shown
   * @returns {boolean}
   */
  is_rendered() {
    return !this.is_pending && (!this.parent || this.parent.is_rendered());
  }
  has_pending_snippet() {
    return !!this.#props.pending;
  }
  /**
   * @template T
   * @param {() => T} fn
   */
  #run(fn) {
    var previous_effect = active_effect;
    var previous_reaction = active_reaction;
    var previous_ctx = component_context;
    set_active_effect(this.#effect);
    set_active_reaction(this.#effect);
    set_component_context(this.#effect.ctx);
    try {
      Batch.ensure();
      return fn();
    } finally {
      set_active_effect(previous_effect);
      set_active_reaction(previous_reaction);
      set_component_context(previous_ctx);
    }
  }
  /**
   * Updates the pending count associated with the currently visible pending snippet,
   * if any, such that we can replace the snippet with content once work is done
   * @param {1 | -1} d
   * @param {Batch} batch
   */
  #update_pending_count(d, batch) {
    if (!this.has_pending_snippet()) {
      if (this.parent) {
        this.parent.#update_pending_count(d, batch);
      }
      return;
    }
    this.#pending_count += d;
    if (this.#pending_count === 0) {
      this.#resolve(batch);
      if (this.#pending_effect) {
        pause_effect(this.#pending_effect, () => {
          this.#pending_effect = null;
        });
      }
      if (this.#offscreen_fragment) {
        this.#anchor.before(this.#offscreen_fragment);
        this.#offscreen_fragment = null;
      }
    }
  }
  /**
   * Update the source that powers `$effect.pending()` inside this boundary,
   * and controls when the current `pending` snippet (if any) is removed.
   * Do not call from inside the class
   * @param {1 | -1} d
   * @param {Batch} batch
   */
  update_pending_count(d, batch) {
    this.#update_pending_count(d, batch);
    this.#local_pending_count += d;
    if (!this.#effect_pending || this.#pending_count_update_queued) return;
    this.#pending_count_update_queued = true;
    queue_micro_task(() => {
      this.#pending_count_update_queued = false;
      if (this.#effect_pending) {
        internal_set(this.#effect_pending, this.#local_pending_count);
      }
    });
  }
  get_effect_pending() {
    this.#effect_pending_subscriber();
    return get(
      /** @type {Source<number>} */
      this.#effect_pending
    );
  }
  /** @param {unknown} error */
  error(error) {
    if (!this.#props.onerror && !this.#props.failed) {
      throw error;
    }
    if (current_batch?.is_fork) {
      if (this.#main_effect) current_batch.skip_effect(this.#main_effect);
      if (this.#pending_effect) current_batch.skip_effect(this.#pending_effect);
      if (this.#failed_effect) current_batch.skip_effect(this.#failed_effect);
      current_batch.oncommit(() => {
        this.#handle_error(error);
      });
    } else {
      this.#handle_error(error);
    }
  }
  /**
   * @param {unknown} error
   */
  #handle_error(error) {
    if (this.#main_effect) {
      destroy_effect(this.#main_effect);
      this.#main_effect = null;
    }
    if (this.#pending_effect) {
      destroy_effect(this.#pending_effect);
      this.#pending_effect = null;
    }
    if (this.#failed_effect) {
      destroy_effect(this.#failed_effect);
      this.#failed_effect = null;
    }
    if (hydrating) {
      set_hydrate_node(
        /** @type {TemplateNode} */
        this.#hydrate_open
      );
      next();
      set_hydrate_node(skip_nodes());
    }
    let failed = this.#props.failed;
    const handle_error_result = (transformed_error) => {
      const { reset: reset2, invoke_onerror } = this.#create_reset(transformed_error);
      invoke_onerror();
      if (failed) {
        this.#failed_effect = this.#run(() => {
          try {
            return branch(() => {
              var effect2 = (
                /** @type {Effect} */
                active_effect
              );
              effect2.b = this;
              effect2.f |= BOUNDARY_EFFECT;
              failed(
                this.#anchor,
                () => transformed_error,
                () => reset2
              );
            });
          } catch (error2) {
            invoke_error_boundary(
              error2,
              /** @type {Effect} */
              this.#effect.parent
            );
            return null;
          }
        });
      }
    };
    queue_micro_task(() => {
      var result;
      try {
        result = this.transform_error(error);
      } catch (e) {
        invoke_error_boundary(e, this.#effect && this.#effect.parent);
        return;
      }
      if (result !== null && typeof result === "object" && typeof /** @type {any} */
      result.then === "function") {
        result.then(
          handle_error_result,
          /** @param {unknown} e */
          (e) => invoke_error_boundary(e, this.#effect && this.#effect.parent)
        );
      } else {
        handle_error_result(result);
      }
    });
  }
};

// node_modules/svelte/src/internal/client/render.js
var should_intro = true;
function set_text(text2, value) {
  var str = value == null ? "" : typeof value === "object" ? `${value}` : value;
  if (str !== /** @type {any} */
  (text2[TEXT_CACHE] ??= text2.nodeValue)) {
    text2[TEXT_CACHE] = str;
    text2.nodeValue = `${str}`;
  }
}
function mount(component2, options) {
  return _mount(component2, options);
}
function hydrate(component2, options) {
  init_operations();
  options.intro = options.intro ?? false;
  const target = options.target;
  const was_hydrating = hydrating;
  const previous_hydrate_node = hydrate_node;
  try {
    var anchor = get_first_child(target);
    while (anchor && (anchor.nodeType !== COMMENT_NODE || /** @type {Comment} */
    anchor.data !== HYDRATION_START)) {
      anchor = get_next_sibling(anchor);
    }
    if (!anchor) {
      throw HYDRATION_ERROR;
    }
    set_hydrating(true);
    set_hydrate_node(
      /** @type {Comment} */
      anchor
    );
    const instance = _mount(component2, { ...options, anchor });
    set_hydrating(false);
    return (
      /**  @type {Exports} */
      instance
    );
  } catch (error) {
    if (error instanceof Error && error.message.split("\n").some((line) => line.startsWith("https://svelte.dev/e/"))) {
      throw error;
    }
    if (error !== HYDRATION_ERROR) {
      console.warn("Failed to hydrate: ", error);
    }
    if (options.recover === false) {
      hydration_failed();
    }
    init_operations();
    clear_text_content(target);
    set_hydrating(false);
    return mount(component2, options);
  } finally {
    set_hydrating(was_hydrating);
    set_hydrate_node(previous_hydrate_node);
  }
}
var listeners = /* @__PURE__ */ new Map();
function _mount(Component, { target, anchor, props = {}, events, context, intro = true, transformError }) {
  init_operations();
  var component2 = void 0;
  var unmount2 = component_root(() => {
    var anchor_node = anchor ?? target.appendChild(create_text());
    boundary(
      /** @type {TemplateNode} */
      anchor_node,
      {
        pending: () => {
        }
      },
      (anchor_node2) => {
        push({});
        var ctx = (
          /** @type {ComponentContext} */
          component_context
        );
        if (context) ctx.c = context;
        if (events) {
          props.$$events = events;
        }
        if (hydrating) {
          assign_nodes(
            /** @type {TemplateNode} */
            anchor_node2,
            null
          );
        }
        should_intro = intro;
        component2 = Component(anchor_node2, props) || mark_as_component();
        should_intro = true;
        if (hydrating) {
          active_effect.nodes.end = hydrate_node;
          if (hydrate_node === null || hydrate_node.nodeType !== COMMENT_NODE || /** @type {Comment} */
          hydrate_node.data !== HYDRATION_END) {
            hydration_mismatch();
            throw HYDRATION_ERROR;
          }
        }
        pop();
      },
      transformError
    );
    var registered_events = /* @__PURE__ */ new Set();
    var event_handle = (events2) => {
      for (var i = 0; i < events2.length; i++) {
        var event_name = events2[i];
        if (registered_events.has(event_name)) continue;
        registered_events.add(event_name);
        var passive2 = is_passive_event(event_name);
        for (const node of [target, document]) {
          var counts = listeners.get(node);
          if (counts === void 0) {
            counts = /* @__PURE__ */ new Map();
            listeners.set(node, counts);
          }
          var count = counts.get(event_name);
          if (count === void 0) {
            node.addEventListener(event_name, handle_event_propagation, { passive: passive2 });
            counts.set(event_name, 1);
          } else {
            counts.set(event_name, count + 1);
          }
        }
      }
    };
    event_handle(array_from(all_registered_events));
    root_event_handles.add(event_handle);
    return () => {
      for (var event_name of registered_events) {
        for (const node of [target, document]) {
          var counts = (
            /** @type {Map<string, number>} */
            listeners.get(node)
          );
          var count = (
            /** @type {number} */
            counts.get(event_name)
          );
          if (--count == 0) {
            node.removeEventListener(event_name, handle_event_propagation);
            counts.delete(event_name);
            if (counts.size === 0) {
              listeners.delete(node);
            }
          } else {
            counts.set(event_name, count);
          }
        }
      }
      root_event_handles.delete(event_handle);
      if (anchor_node !== anchor) {
        anchor_node.parentNode?.removeChild(anchor_node);
      }
    };
  });
  mounted_components.set(component2, unmount2);
  return component2;
}
var mounted_components = /* @__PURE__ */ new WeakMap();
function unmount(component2, options) {
  const fn = mounted_components.get(component2);
  if (fn) {
    mounted_components.delete(component2);
    return fn(options);
  }
  if (dev_fallback_default) {
    lifecycle_double_unmount();
  }
  return Promise.resolve();
}

// node_modules/svelte/src/internal/client/dom/blocks/branches.js
var BranchManager = class {
  /** @type {TemplateNode} */
  anchor;
  /** @type {Map<Batch, Key>} */
  #batches = /* @__PURE__ */ new Map();
  /**
   * Map of keys to effects that are currently rendered in the DOM.
   * These effects are visible and actively part of the document tree.
   * Example:
   * ```
   * {#if condition}
   * 	foo
   * {:else}
   * 	bar
   * {/if}
   * ```
   * Can result in the entries `true->Effect` and `false->Effect`
   * @type {Map<Key, Effect>}
   */
  #onscreen = /* @__PURE__ */ new Map();
  /**
   * Similar to #onscreen with respect to the keys, but contains branches that are not yet
   * in the DOM, because their insertion is deferred.
   * @type {Map<Key, Branch>}
   */
  #offscreen = /* @__PURE__ */ new Map();
  /**
   * Keys of effects that are currently outroing
   * @type {Set<Key>}
   */
  #outroing = /* @__PURE__ */ new Set();
  /**
   * Whether to pause (i.e. outro) on change, or destroy immediately.
   * This is necessary for `<svelte:element>`
   */
  #transition = true;
  /**
   * @param {TemplateNode} anchor
   * @param {boolean} transition
   */
  constructor(anchor, transition2 = true) {
    this.anchor = anchor;
    this.#transition = transition2;
  }
  /**
   * @param {Batch} batch
   */
  #commit = (batch) => {
    if (!this.#batches.has(batch)) return;
    var key2 = (
      /** @type {Key} */
      this.#batches.get(batch)
    );
    var onscreen = this.#onscreen.get(key2);
    if (onscreen) {
      resume_effect(onscreen);
      this.#outroing.delete(key2);
    } else {
      var offscreen = this.#offscreen.get(key2);
      if (offscreen) {
        resume_effect(offscreen.effect);
        this.#onscreen.set(key2, offscreen.effect);
        this.#offscreen.delete(key2);
        if (dev_fallback_default) {
          offscreen.fragment.lastChild[HMR_ANCHOR] = this.anchor;
        }
        offscreen.fragment.lastChild.remove();
        this.anchor.before(offscreen.fragment);
        onscreen = offscreen.effect;
      }
    }
    for (const [b, k] of this.#batches) {
      this.#batches.delete(b);
      if (b === batch) {
        break;
      }
      const offscreen2 = this.#offscreen.get(k);
      if (offscreen2) {
        destroy_effect(offscreen2.effect);
        this.#offscreen.delete(k);
      }
    }
    for (const [k, effect2] of this.#onscreen) {
      if (k === key2 || this.#outroing.has(k)) continue;
      const on_destroy = () => {
        const keys = Array.from(this.#batches.values());
        if (keys.includes(k)) {
          var fragment = document.createDocumentFragment();
          move_effect(effect2, fragment);
          fragment.append(create_text());
          this.#offscreen.set(k, { effect: effect2, fragment });
        } else {
          destroy_effect(effect2);
        }
        this.#outroing.delete(k);
        this.#onscreen.delete(k);
      };
      if (this.#transition || !onscreen) {
        this.#outroing.add(k);
        pause_effect(effect2, on_destroy, false);
      } else {
        on_destroy();
      }
    }
  };
  /**
   * @param {Batch} batch
   */
  #discard = (batch) => {
    this.#batches.delete(batch);
    const keys = Array.from(this.#batches.values());
    for (const [k, branch2] of this.#offscreen) {
      if (!keys.includes(k)) {
        destroy_effect(branch2.effect);
        this.#offscreen.delete(k);
      }
    }
  };
  /**
   *
   * @param {any} key
   * @param {null | ((target: TemplateNode) => void)} fn
   */
  ensure(key2, fn) {
    var batch = (
      /** @type {Batch} */
      current_batch
    );
    var defer = should_defer_append();
    if (fn && !this.#onscreen.has(key2) && !this.#offscreen.has(key2)) {
      if (defer) {
        var fragment = document.createDocumentFragment();
        var target = create_text();
        fragment.append(target);
        this.#offscreen.set(key2, {
          effect: branch(() => fn(target)),
          fragment
        });
      } else {
        this.#onscreen.set(
          key2,
          branch(() => fn(this.anchor))
        );
      }
    }
    this.#batches.set(batch, key2);
    if (defer) {
      for (const [k, effect2] of this.#onscreen) {
        if (k === key2) {
          batch.unskip_effect(effect2);
        } else {
          batch.skip_effect(effect2);
        }
      }
      for (const [k, branch2] of this.#offscreen) {
        if (k === key2) {
          batch.unskip_effect(branch2.effect);
        } else {
          batch.skip_effect(branch2.effect);
        }
      }
      batch.oncommit(this.#commit);
      batch.ondiscard(this.#discard);
    } else {
      if (hydrating) {
        this.anchor = hydrate_node;
      }
      this.#commit(batch);
    }
  }
};

// node_modules/svelte/src/internal/client/dom/blocks/if.js
function if_block(node, fn, elseif = false) {
  var marker;
  if (hydrating) {
    marker = hydrate_node;
    hydrate_next();
  }
  var branches = new BranchManager(node);
  var flags2 = elseif ? EFFECT_TRANSPARENT : 0;
  function update_branch(key2, fn2) {
    if (hydrating) {
      var data = read_hydration_instruction(
        /** @type {TemplateNode} */
        marker
      );
      if (key2 !== parseInt(data.substring(1))) {
        var anchor = skip_nodes();
        set_hydrate_node(anchor);
        branches.anchor = anchor;
        set_hydrating(false);
        branches.ensure(key2, fn2);
        set_hydrating(true);
        return;
      }
    }
    branches.ensure(key2, fn2);
  }
  block(() => {
    var has_branch = false;
    fn((fn2, key2 = 0) => {
      has_branch = true;
      update_branch(key2, fn2);
    });
    if (!has_branch) {
      update_branch(-1, null);
    }
  }, flags2);
}

// node_modules/svelte/src/internal/client/dom/blocks/key.js
var NAN = Symbol("NaN");

// node_modules/svelte/src/internal/client/dom/blocks/each.js
function index(_, i) {
  return i;
}
function pause_effects(state2, to_destroy, controlled_anchor) {
  var transitions = [];
  var length = to_destroy.length;
  var group;
  var remaining = to_destroy.length;
  for (var i = 0; i < length; i++) {
    let effect2 = to_destroy[i];
    pause_effect(
      effect2,
      () => {
        if (group) {
          group.pending.delete(effect2);
          group.done.add(effect2);
          if (group.pending.size === 0) {
            var groups = (
              /** @type {Set<EachOutroGroup>} */
              state2.outrogroups
            );
            destroy_effects(state2, array_from(group.done));
            groups.delete(group);
            if (groups.size === 0) {
              state2.outrogroups = null;
            }
          }
        } else {
          remaining -= 1;
        }
      },
      false
    );
  }
  if (remaining === 0) {
    var fast_path = transitions.length === 0 && controlled_anchor !== null && state2.pending.size === 0;
    if (fast_path) {
      var anchor = (
        /** @type {Element} */
        controlled_anchor
      );
      var parent_node = (
        /** @type {Element} */
        anchor.parentNode
      );
      clear_text_content(parent_node);
      parent_node.append(anchor);
      state2.items.clear();
    }
    destroy_effects(state2, to_destroy, !fast_path);
  } else {
    group = {
      pending: new Set(to_destroy),
      done: /* @__PURE__ */ new Set()
    };
    (state2.outrogroups ??= /* @__PURE__ */ new Set()).add(group);
  }
}
function destroy_effects(state2, to_destroy, remove_dom = true) {
  var preserved_effects;
  if (state2.pending.size > 0) {
    preserved_effects = /* @__PURE__ */ new Set();
    for (const keys of state2.pending.values()) {
      for (const key2 of keys) {
        preserved_effects.add(
          /** @type {EachItem} */
          state2.items.get(key2).e
        );
      }
    }
  }
  for (var i = 0; i < to_destroy.length; i++) {
    var e = to_destroy[i];
    if (preserved_effects?.has(e)) {
      e.f |= EFFECT_OFFSCREEN;
      const fragment = document.createDocumentFragment();
      move_effect(e, fragment);
    } else {
      destroy_effect(to_destroy[i], remove_dom);
    }
  }
}
var offscreen_anchor;
function each(node, flags2, get_collection, get_key, render_fn, fallback_fn = null) {
  var anchor = node;
  var items = /* @__PURE__ */ new Map();
  var is_controlled = (flags2 & EACH_IS_CONTROLLED) !== 0;
  if (is_controlled) {
    var parent_node = (
      /** @type {Element} */
      node
    );
    anchor = hydrating ? set_hydrate_node(get_first_child(parent_node)) : parent_node.appendChild(create_text());
  }
  if (hydrating) {
    hydrate_next();
  }
  var fallback2 = null;
  var each_array = derived_safe_equal(() => {
    var collection = get_collection();
    return (
      /** @type {V[]} */
      is_array(collection) ? collection : collection == null ? [] : array_from(collection)
    );
  });
  if (dev_fallback_default) {
    tag(each_array, "{#each ...}");
  }
  var array;
  var pending2 = /* @__PURE__ */ new Map();
  var first_run = true;
  function commit(batch) {
    if ((state2.effect.f & DESTROYED) !== 0) {
      return;
    }
    state2.pending.delete(batch);
    state2.fallback = fallback2;
    reconcile(state2, array, anchor, flags2, get_key);
    if (fallback2 !== null) {
      if (array.length === 0) {
        if ((fallback2.f & EFFECT_OFFSCREEN) === 0) {
          resume_effect(fallback2);
        } else {
          fallback2.f ^= EFFECT_OFFSCREEN;
          move(fallback2, null, anchor);
        }
      } else {
        pause_effect(fallback2, () => {
          fallback2 = null;
        });
      }
    }
  }
  function discard(batch) {
    state2.pending.delete(batch);
  }
  var effect2 = block(() => {
    array = /** @type {V[]} */
    get(each_array);
    var length = array.length;
    let mismatch = false;
    if (hydrating) {
      var is_else = read_hydration_instruction(anchor) === HYDRATION_START_ELSE;
      if (is_else !== (length === 0)) {
        anchor = skip_nodes();
        set_hydrate_node(anchor);
        set_hydrating(false);
        mismatch = true;
      }
    }
    var keys = /* @__PURE__ */ new Set();
    var batch = (
      /** @type {Batch} */
      current_batch
    );
    var defer = should_defer_append();
    for (var index2 = 0; index2 < length; index2 += 1) {
      if (hydrating && hydrate_node.nodeType === COMMENT_NODE && /** @type {Comment} */
      hydrate_node.data === HYDRATION_END) {
        anchor = /** @type {Comment} */
        hydrate_node;
        mismatch = true;
        set_hydrating(false);
      }
      var value = array[index2];
      var key2 = get_key(value, index2);
      if (dev_fallback_default) {
        var key_again = get_key(value, index2);
        if (key2 !== key_again) {
          each_key_volatile(String(index2), String(key2), String(key_again));
        }
      }
      var item = first_run ? null : items.get(key2);
      if (item) {
        if (item.v) internal_set(item.v, value);
        if (item.i) internal_set(item.i, index2);
        if (defer) {
          batch.unskip_effect(item.e);
        }
      } else {
        item = create_item(
          items,
          first_run ? anchor : offscreen_anchor ??= create_text(),
          value,
          key2,
          index2,
          render_fn,
          flags2,
          get_collection
        );
        if (!first_run) {
          item.e.f |= EFFECT_OFFSCREEN;
        }
        items.set(key2, item);
      }
      keys.add(key2);
    }
    if (length === 0 && fallback_fn && !fallback2) {
      if (first_run) {
        fallback2 = branch(() => fallback_fn(anchor));
      } else {
        fallback2 = branch(() => fallback_fn(offscreen_anchor ??= create_text()));
        fallback2.f |= EFFECT_OFFSCREEN;
      }
    }
    if (length > keys.size) {
      if (dev_fallback_default) {
        validate_each_keys(array, get_key);
      } else {
        each_key_duplicate("", "", "");
      }
    }
    if (hydrating && length > 0) {
      set_hydrate_node(skip_nodes());
    }
    if (!first_run) {
      pending2.set(batch, keys);
      if (defer) {
        for (const [key3, item2] of items) {
          if (!keys.has(key3)) {
            batch.skip_effect(item2.e);
          }
        }
        batch.oncommit(commit);
        batch.ondiscard(discard);
      } else {
        commit(batch);
      }
    }
    if (mismatch) {
      set_hydrating(true);
    }
    get(each_array);
  });
  var state2 = { effect: effect2, flags: flags2, items, pending: pending2, outrogroups: null, fallback: fallback2 };
  first_run = false;
  if (hydrating) {
    anchor = hydrate_node;
  }
}
function skip_to_branch(effect2) {
  while (effect2 !== null && (effect2.f & BRANCH_EFFECT) === 0) {
    effect2 = effect2.next;
  }
  return effect2;
}
function reconcile(state2, array, anchor, flags2, get_key) {
  var is_animated = (flags2 & EACH_IS_ANIMATED) !== 0;
  var length = array.length;
  var items = state2.items;
  var current = skip_to_branch(state2.effect.first);
  var seen2;
  var prev = null;
  var to_animate;
  var matched = [];
  var stashed = [];
  var value;
  var key2;
  var effect2;
  var i;
  if (is_animated) {
    for (i = 0; i < length; i += 1) {
      value = array[i];
      key2 = get_key(value, i);
      effect2 = /** @type {EachItem} */
      items.get(key2).e;
      if ((effect2.f & EFFECT_OFFSCREEN) === 0) {
        effect2.nodes?.a?.measure();
        (to_animate ??= /* @__PURE__ */ new Set()).add(effect2);
      }
    }
  }
  for (i = 0; i < length; i += 1) {
    value = array[i];
    key2 = get_key(value, i);
    effect2 = /** @type {EachItem} */
    items.get(key2).e;
    if (state2.outrogroups !== null) {
      for (const group of state2.outrogroups) {
        group.pending.delete(effect2);
        group.done.delete(effect2);
      }
    }
    if ((effect2.f & INERT) !== 0) {
      resume_effect(effect2);
      if (is_animated) {
        effect2.nodes?.a?.unfix();
        (to_animate ??= /* @__PURE__ */ new Set()).delete(effect2);
      }
    }
    if ((effect2.f & EFFECT_OFFSCREEN) !== 0) {
      effect2.f ^= EFFECT_OFFSCREEN;
      if (effect2 === current) {
        move(effect2, null, anchor);
      } else {
        var next2 = prev ? prev.next : current;
        if (effect2 === state2.effect.last) {
          state2.effect.last = effect2.prev;
        }
        if (effect2.prev) effect2.prev.next = effect2.next;
        if (effect2.next) effect2.next.prev = effect2.prev;
        link(state2, prev, effect2);
        link(state2, effect2, next2);
        move(effect2, next2, anchor);
        prev = effect2;
        matched = [];
        stashed = [];
        current = skip_to_branch(prev.next);
        continue;
      }
    }
    if (effect2 !== current) {
      if (seen2 !== void 0 && seen2.has(effect2)) {
        if (matched.length < stashed.length) {
          var start = stashed[0];
          var j;
          prev = start.prev;
          var a = matched[0];
          var b = matched[matched.length - 1];
          for (j = 0; j < matched.length; j += 1) {
            move(matched[j], start, anchor);
          }
          for (j = 0; j < stashed.length; j += 1) {
            seen2.delete(stashed[j]);
          }
          link(state2, a.prev, b.next);
          link(state2, prev, a);
          link(state2, b, start);
          current = start;
          prev = b;
          i -= 1;
          matched = [];
          stashed = [];
        } else {
          seen2.delete(effect2);
          move(effect2, current, anchor);
          link(state2, effect2.prev, effect2.next);
          link(state2, effect2, prev === null ? state2.effect.first : prev.next);
          link(state2, prev, effect2);
          prev = effect2;
        }
        continue;
      }
      matched = [];
      stashed = [];
      while (current !== null && current !== effect2) {
        (seen2 ??= /* @__PURE__ */ new Set()).add(current);
        stashed.push(current);
        current = skip_to_branch(current.next);
      }
      if (current === null) {
        continue;
      }
    }
    if ((effect2.f & EFFECT_OFFSCREEN) === 0) {
      matched.push(effect2);
    }
    prev = effect2;
    current = skip_to_branch(effect2.next);
  }
  if (state2.outrogroups !== null) {
    for (const group of state2.outrogroups) {
      if (group.pending.size === 0) {
        destroy_effects(state2, array_from(group.done));
        state2.outrogroups?.delete(group);
      }
    }
    if (state2.outrogroups.size === 0) {
      state2.outrogroups = null;
    }
  }
  if (current !== null || seen2 !== void 0) {
    var to_destroy = [];
    if (seen2 !== void 0) {
      for (effect2 of seen2) {
        if ((effect2.f & INERT) === 0) {
          to_destroy.push(effect2);
        }
      }
    }
    while (current !== null) {
      if ((current.f & INERT) === 0 && current !== state2.fallback) {
        to_destroy.push(current);
      }
      current = skip_to_branch(current.next);
    }
    var destroy_length = to_destroy.length;
    if (destroy_length > 0) {
      var controlled_anchor = (flags2 & EACH_IS_CONTROLLED) !== 0 && length === 0 ? anchor : null;
      if (is_animated) {
        for (i = 0; i < destroy_length; i += 1) {
          to_destroy[i].nodes?.a?.measure();
        }
        for (i = 0; i < destroy_length; i += 1) {
          to_destroy[i].nodes?.a?.fix();
        }
      }
      pause_effects(state2, to_destroy, controlled_anchor);
    }
  }
  if (is_animated) {
    queue_micro_task(() => {
      if (to_animate === void 0) return;
      for (effect2 of to_animate) {
        effect2.nodes?.a?.apply();
      }
    });
  }
}
function create_item(items, anchor, value, key2, index2, render_fn, flags2, get_collection) {
  var v = (flags2 & EACH_ITEM_REACTIVE) !== 0 ? (flags2 & EACH_ITEM_IMMUTABLE) === 0 ? mutable_source(value, false, false) : source(value) : null;
  var i = (flags2 & EACH_INDEX_REACTIVE) !== 0 ? source(index2) : null;
  if (dev_fallback_default && v) {
    v.trace = () => {
      get_collection()[i?.v ?? index2];
    };
  }
  return {
    v,
    i,
    e: branch(() => {
      render_fn(anchor, v ?? value, i ?? index2, get_collection);
      return () => {
        items.delete(key2);
      };
    })
  };
}
function move(effect2, next2, anchor) {
  if (!effect2.nodes) return;
  var node = effect2.nodes.start;
  var end = effect2.nodes.end;
  var dest = next2 && (next2.f & EFFECT_OFFSCREEN) === 0 ? (
    /** @type {EffectNodes} */
    next2.nodes.start
  ) : anchor;
  while (node !== null) {
    var next_node = (
      /** @type {TemplateNode} */
      get_next_sibling(node)
    );
    dest.before(node);
    if (node === end) {
      return;
    }
    node = next_node;
  }
}
function link(state2, prev, next2) {
  if (prev === null) {
    state2.effect.first = next2;
  } else {
    prev.next = next2;
  }
  if (next2 === null) {
    state2.effect.last = prev;
  } else {
    next2.prev = prev;
  }
}
function validate_each_keys(array, key_fn) {
  const keys = /* @__PURE__ */ new Map();
  const length = array.length;
  for (let i = 0; i < length; i++) {
    const key2 = key_fn(array[i], i);
    if (keys.has(key2)) {
      const a = String(keys.get(key2));
      const b = String(i);
      let k = String(key2);
      if (k.startsWith("[object ")) k = null;
      each_key_duplicate(a, b, k);
    }
    keys.set(key2, i);
  }
}

// node_modules/svelte/src/internal/shared/attributes.js
var whitespace = [..." 	\n\r\f\xA0\v\uFEFF"];
function to_class(value, hash2, directives) {
  var classname = value == null ? "" : "" + value;
  if (hash2) {
    classname = classname ? classname + " " + hash2 : hash2;
  }
  if (directives) {
    for (var key2 of Object.keys(directives)) {
      if (directives[key2]) {
        classname = classname ? classname + " " + key2 : key2;
      } else if (classname.length) {
        var len = key2.length;
        var a = 0;
        while ((a = classname.indexOf(key2, a)) >= 0) {
          var b = a + len;
          if ((a === 0 || whitespace.includes(classname[a - 1])) && (b === classname.length || whitespace.includes(classname[b]))) {
            classname = (a === 0 ? "" : classname.substring(0, a)) + classname.substring(b + 1);
          } else {
            a = b;
          }
        }
      }
    }
  }
  return classname === "" ? null : classname;
}
function append_styles(styles, important = false) {
  var separator = important ? " !important;" : ";";
  var css = "";
  for (var key2 of Object.keys(styles)) {
    var value = styles[key2];
    if (value != null && value !== "") {
      css += " " + key2 + ": " + value + separator;
    }
  }
  return css;
}
function to_css_name(name) {
  if (name[0] !== "-" || name[1] !== "-") {
    return name.toLowerCase();
  }
  return name;
}
function to_style(value, styles) {
  if (styles) {
    var new_style = "";
    var normal_styles;
    var important_styles;
    if (Array.isArray(styles)) {
      normal_styles = styles[0];
      important_styles = styles[1];
    } else {
      normal_styles = styles;
    }
    if (value) {
      value = String(value).replaceAll(/\/\*.*?\*\//g, "").trim();
      var in_str = false;
      var in_apo = 0;
      var in_comment = false;
      var reserved_names = [];
      if (normal_styles) {
        reserved_names.push(...Object.keys(normal_styles).map(to_css_name));
      }
      if (important_styles) {
        reserved_names.push(...Object.keys(important_styles).map(to_css_name));
      }
      var start_index = 0;
      var name_index = -1;
      const len = value.length;
      for (var i = 0; i < len; i++) {
        var c = value[i];
        if (in_comment) {
          if (c === "/" && value[i - 1] === "*") {
            in_comment = false;
          }
        } else if (in_str) {
          if (in_str === c) {
            in_str = false;
          }
        } else if (c === "/" && value[i + 1] === "*") {
          in_comment = true;
        } else if (c === '"' || c === "'") {
          in_str = c;
        } else if (c === "(") {
          in_apo++;
        } else if (c === ")") {
          in_apo--;
        }
        if (!in_comment && in_str === false && in_apo === 0) {
          if (c === ":" && name_index === -1) {
            name_index = i;
          } else if (c === ";" || i === len - 1) {
            if (name_index !== -1) {
              var name = to_css_name(value.substring(start_index, name_index).trim());
              if (!reserved_names.includes(name)) {
                if (c !== ";") {
                  i++;
                }
                var property = value.substring(start_index, i).trim();
                new_style += " " + property + ";";
              }
            }
            start_index = i + 1;
            name_index = -1;
          }
        }
      }
    }
    if (normal_styles) {
      new_style += append_styles(normal_styles);
    }
    if (important_styles) {
      new_style += append_styles(important_styles, true);
    }
    new_style = new_style.trim();
    return new_style === "" ? null : new_style;
  }
  return value == null ? null : String(value);
}

// node_modules/svelte/src/internal/client/dom/elements/class.js
function set_class(dom, is_html, value, hash2, prev_classes, next_classes) {
  var prev = (
    /** @type {any} */
    dom[CLASS_CACHE]
  );
  if (hydrating || prev !== value || prev === void 0) {
    var next_class_name = to_class(value, hash2, next_classes);
    if (!hydrating || next_class_name !== dom.getAttribute("class")) {
      if (next_class_name == null) {
        dom.removeAttribute("class");
      } else if (is_html) {
        dom.className = next_class_name;
      } else {
        dom.setAttribute("class", next_class_name);
      }
    }
    dom[CLASS_CACHE] = value;
  } else if (next_classes && prev_classes !== next_classes) {
    for (var key2 in next_classes) {
      var is_present = !!next_classes[key2];
      if (prev_classes == null || is_present !== !!prev_classes[key2]) {
        dom.classList.toggle(key2, is_present);
      }
    }
  }
  return next_classes;
}

// node_modules/svelte/src/internal/client/dom/elements/style.js
function update_styles(dom, prev = {}, next2, priority) {
  for (var key2 in next2) {
    var value = next2[key2];
    if (prev[key2] !== value) {
      if (next2[key2] == null) {
        dom.style.removeProperty(key2);
      } else {
        dom.style.setProperty(key2, value, priority);
      }
    }
  }
}
function set_style(dom, value, prev_styles, next_styles) {
  var prev = (
    /** @type {any} */
    dom[STYLE_CACHE]
  );
  if (hydrating || prev !== value) {
    var next_style_attr = to_style(value, next_styles);
    if (!hydrating || next_style_attr !== dom.getAttribute("style")) {
      if (next_style_attr == null) {
        dom.removeAttribute("style");
      } else {
        dom.style.cssText = next_style_attr;
      }
    }
    dom[STYLE_CACHE] = value;
  } else if (next_styles) {
    if (Array.isArray(next_styles)) {
      update_styles(dom, prev_styles?.[0], next_styles[0]);
      update_styles(dom, prev_styles?.[1], next_styles[1], "important");
    } else {
      update_styles(dom, prev_styles, next_styles);
    }
  }
  return next_styles;
}

// node_modules/svelte/src/internal/client/dom/elements/bindings/select.js
function set_selected(option, selected) {
  if (selected) {
    if (!option.hasAttribute("selected")) option.setAttribute("selected", "");
  } else {
    option.removeAttribute("selected");
  }
}
function apply_default_select_value(select, preserve) {
  var value = select.__defaultValue;
  var multiple = select.multiple;
  var values = multiple ? value ?? [] : null;
  if (multiple && !is_array(values)) return;
  var index2 = select.selectedIndex;
  var selected = preserve && multiple ? new Set(select.selectedOptions) : null;
  for (var option of select.options) {
    var option_value = get_option_value(option);
    set_selected(
      option,
      multiple ? (
        /** @type {any[]} */
        values.includes(option_value)
      ) : is(option_value, value)
    );
  }
  if (!preserve) return;
  if (selected !== null) {
    for (option of select.options) {
      var was_selected = selected.has(option);
      if (option.selected !== was_selected) option.selected = was_selected;
    }
  } else if (select.selectedIndex !== index2) {
    select.selectedIndex = index2;
  }
}
function select_option(select, value, mounting = false) {
  if (select.multiple) {
    if (value == void 0) {
      return;
    }
    if (!is_array(value)) {
      return select_multiple_invalid_value();
    }
    for (var option of select.options) {
      option.selected = value.includes(get_option_value(option));
    }
    return;
  }
  for (option of select.options) {
    var option_value = get_option_value(option);
    if (is(option_value, value)) {
      option.selected = true;
      return;
    }
  }
  if (!mounting || value !== void 0) {
    select.selectedIndex = -1;
  }
}
function init_select(select) {
  var observer = new MutationObserver((entries) => {
    if (entries.every(is_selectedcontent_mutation)) return;
    if ("__defaultValue" in select) {
      apply_default_select_value(select, false);
    }
    if ("__value" in select) {
      select_option(select, select.__value);
    }
  });
  observer.observe(select, {
    // Listen to option element changes
    childList: true,
    subtree: true,
    // because of <optgroup>
    // Listen to option element value attribute changes
    // (doesn't get notified of select value changes,
    // because that property is not reflected as an attribute)
    attributes: true,
    attributeFilter: ["value"]
  });
  teardown(() => {
    observer.disconnect();
  });
}
function bind_select_value(select, get3, set2 = get3) {
  var batches = /* @__PURE__ */ new WeakSet();
  var mounting = true;
  listen_to_event_and_reset_event(select, "change", (is_reset) => {
    var query = is_reset ? "[selected]" : ":checked";
    var value;
    if (select.multiple) {
      value = [].map.call(select.querySelectorAll(query), get_option_value);
    } else {
      var selected_option = select.querySelector(query) ?? // will fall back to first non-disabled option if no option is selected
      select.querySelector("option:not([disabled])");
      value = selected_option && get_option_value(selected_option);
    }
    set2(value);
    select.__value = value;
    if (current_batch !== null) {
      batches.add(current_batch);
    }
  });
  effect(() => {
    var value = get3();
    if (select === document.activeElement) {
      var batch = (
        /** @type {Batch} */
        async_mode_flag ? previous_batch : current_batch
      );
      if (batches.has(batch)) {
        return;
      }
    }
    select_option(select, value, mounting);
    if (mounting && value === void 0) {
      var selected_option = select.querySelector(":checked");
      if (selected_option !== null) {
        value = get_option_value(selected_option);
        set2(value);
      }
    }
    select.__value = value;
    mounting = false;
  });
}
function get_option_value(option) {
  if ("__value" in option) {
    return option.__value;
  } else {
    return option.value;
  }
}
function is_selectedcontent_mutation(entry) {
  if (
    /** @type {Element} */
    entry.target.closest("selectedcontent") !== null
  ) {
    return true;
  }
  if (entry.type === "childList") {
    var nodes = [...entry.addedNodes, ...entry.removedNodes];
    return nodes.length > 0 && nodes.every((node) => node.nodeName === "SELECTEDCONTENT");
  }
  return false;
}

// node_modules/svelte/src/internal/client/dom/elements/attributes.js
var CLASS = Symbol("class");
var STYLE = Symbol("style");
var IS_CUSTOM_ELEMENT = Symbol("is custom element");
var IS_HTML = Symbol("is html");
var LINK_TAG = IS_XHTML ? "link" : "LINK";
var PROGRESS_TAG = IS_XHTML ? "progress" : "PROGRESS";
function remove_input_defaults(input) {
  if (!hydrating) return;
  var already_removed = false;
  var remove_defaults = () => {
    if (already_removed) return;
    already_removed = true;
    if (input.hasAttribute("value")) {
      var value = input.value;
      set_attribute2(input, "value", null);
      input.value = value;
    }
    if (input.hasAttribute("checked")) {
      var checked = input.checked;
      set_attribute2(input, "checked", null);
      input.checked = checked;
    }
  };
  input[FORM_RESET_HANDLER] = remove_defaults;
  queue_micro_task(remove_defaults);
  add_form_reset_listener();
}
function set_value(element2, value) {
  var attributes = get_attributes(element2);
  if (attributes.value === (attributes.value = // treat null and undefined the same for the initial value
  value ?? void 0) || // @ts-expect-error
  // `progress` elements always need their value set when it's `0`
  element2.value === value && (value !== 0 || element2.nodeName !== PROGRESS_TAG)) {
    return;
  }
  element2.value = value ?? "";
}
function set_checked(element2, checked) {
  var attributes = get_attributes(element2);
  if (attributes.checked === (attributes.checked = // treat null and undefined the same for the initial value
  checked ?? void 0)) {
    return;
  }
  element2.checked = checked;
}
function set_attribute2(element2, attribute, value, skip_warning) {
  var attributes = get_attributes(element2);
  if (hydrating) {
    attributes[attribute] = element2.getAttribute(attribute);
    if (attribute === "src" || attribute === "srcset" || attribute === "href" && element2.nodeName === LINK_TAG) {
      if (!skip_warning) {
        check_src_in_dev_hydration(element2, attribute, value ?? "");
      }
      return;
    }
  }
  if (attributes[attribute] === (attributes[attribute] = value)) return;
  if (attribute === "loading") {
    element2[LOADING_ATTR_SYMBOL] = value;
  }
  if (value == null) {
    element2.removeAttribute(attribute);
  } else if (typeof value !== "string" && get_setters(element2).has(attribute)) {
    element2[attribute] = value;
  } else {
    element2.setAttribute(attribute, value);
  }
}
function get_attributes(element2) {
  return (
    /** @type {Record<string | symbol, unknown>} **/
    /** @type {any} */
    element2[ATTRIBUTES_CACHE] ??= {
      [IS_CUSTOM_ELEMENT]: element2.nodeName.includes("-"),
      [IS_HTML]: element2.namespaceURI === NAMESPACE_HTML
    }
  );
}
var setters_cache = /* @__PURE__ */ new Map();
function get_setters(element2) {
  var cache_key = element2.getAttribute("is") || element2.nodeName;
  var setters = setters_cache.get(cache_key);
  if (setters) return setters;
  setters_cache.set(cache_key, setters = /* @__PURE__ */ new Set());
  var descriptors;
  var proto = element2;
  var element_proto = Element.prototype;
  while (element_proto !== proto) {
    descriptors = get_descriptors(proto);
    for (var key2 in descriptors) {
      if (descriptors[key2].set && // better safe than sorry, we don't want spread attributes to mess with HTML content
      key2 !== "innerHTML" && key2 !== "textContent" && key2 !== "innerText") {
        setters.add(key2);
      }
    }
    proto = get_prototype_of(proto);
  }
  return setters;
}
function check_src_in_dev_hydration(element2, attribute, value) {
  if (!dev_fallback_default) return;
  if (attribute === "srcset" && srcset_url_equal(element2, value)) return;
  if (src_url_equal(element2.getAttribute(attribute) ?? "", value)) return;
  hydration_attribute_changed(
    attribute,
    element2.outerHTML.replace(element2.innerHTML, element2.innerHTML && "..."),
    String(value)
  );
}
function src_url_equal(element_src, url) {
  if (element_src === url) return true;
  return new URL(element_src, document.baseURI).href === new URL(url, document.baseURI).href;
}
function split_srcset(srcset) {
  return srcset.split(",").map((src) => src.trim().split(" ").filter(Boolean));
}
function srcset_url_equal(element2, srcset) {
  var element_urls = split_srcset(element2.srcset);
  var urls = split_srcset(srcset);
  return urls.length === element_urls.length && urls.every(
    ([url, width], i) => width === element_urls[i][1] && // We need to test both ways because Vite will create an a full URL with
    // `new URL(asset, import.meta.url).href` for the client when `base: './'`, and the
    // relative URLs inside srcset are not automatically resolved to absolute URLs by
    // browsers (in contrast to img.src). This means both SSR and DOM code could
    // contain relative or absolute URLs.
    (src_url_equal(element_urls[i][0], url) || src_url_equal(url, element_urls[i][0]))
  );
}

// node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function bind_value(input, get3, set2 = get3) {
  var batches = /* @__PURE__ */ new WeakSet();
  listen_to_event_and_reset_event(input, "input", async (is_reset) => {
    if (dev_fallback_default && input.type === "checkbox") {
      bind_invalid_checkbox_value();
    }
    var value = is_reset ? input.defaultValue : input.value;
    value = is_numberlike_input(input) ? to_number(value) : value;
    set2(value);
    if (current_batch !== null) {
      batches.add(current_batch);
    }
    await tick();
    if (value !== (value = get3())) {
      var start = input.selectionStart;
      var end = input.selectionEnd;
      var length = input.value.length;
      input.value = value ?? "";
      if (end !== null) {
        var new_length = input.value.length;
        if (start === end && end === length && new_length > length) {
          input.selectionStart = new_length;
          input.selectionEnd = new_length;
        } else {
          input.selectionStart = start;
          input.selectionEnd = Math.min(end, new_length);
        }
      }
    }
  });
  if (
    // If we are hydrating and the value has since changed,
    // then use the updated value from the input instead.
    hydrating && input.defaultValue !== input.value || // If defaultValue is set, then value == defaultValue
    // TODO Svelte 6: remove input.value check and set to empty string?
    untrack(get3) == null && input.value
  ) {
    set2(is_numberlike_input(input) ? to_number(input.value) : input.value);
    if (current_batch !== null) {
      batches.add(current_batch);
    }
  }
  render_effect(() => {
    if (dev_fallback_default && input.type === "checkbox") {
      bind_invalid_checkbox_value();
    }
    var value = get3();
    if (input === document.activeElement) {
      var batch = (
        /** @type {Batch} */
        async_mode_flag ? previous_batch : current_batch
      );
      if (batches.has(batch)) {
        return;
      }
    }
    if (is_numberlike_input(input) && value === to_number(input.value)) {
      return;
    }
    if (input.type === "date" && !value && !input.value) {
      return;
    }
    if (value !== input.value) {
      input.value = value ?? "";
    }
  });
}
function is_numberlike_input(input) {
  var type = input.type;
  return type === "number" || type === "range";
}
function to_number(value) {
  return value === "" ? null : +value;
}

// node_modules/svelte/src/internal/client/dom/elements/bindings/this.js
function is_bound_this(bound_value, element_or_component) {
  return bound_value === element_or_component || bound_value?.[STATE_SYMBOL] === element_or_component;
}
function bind_this(element_or_component = mark_as_component(), update2, get_value, get_parts) {
  var component_effect = (
    /** @type {ComponentContext} */
    component_context.r
  );
  var parent = (
    /** @type {Effect} */
    active_effect
  );
  effect(() => {
    var old_parts;
    var parts;
    render_effect(() => {
      old_parts = parts;
      parts = get_parts?.() || [];
      untrack(() => {
        if (!is_bound_this(get_value(...parts), element_or_component)) {
          update2(element_or_component, ...parts);
          if (old_parts && is_bound_this(get_value(...old_parts), element_or_component)) {
            update2(null, ...old_parts);
          }
        }
      });
    });
    return () => {
      let p = parent;
      while (p !== component_effect && p.parent !== null && p.parent.f & DESTROYING) {
        p = p.parent;
      }
      const teardown2 = () => {
        if (parts && is_bound_this(get_value(...parts), element_or_component)) {
          update2(null, ...parts);
        }
      };
      const original_teardown = p.teardown;
      p.teardown = () => {
        teardown2();
        original_teardown?.();
      };
    };
  });
  return element_or_component;
}

// node_modules/svelte/src/internal/client/dom/legacy/event-modifiers.js
function stopPropagation(fn) {
  return function(...args) {
    var event2 = (
      /** @type {Event} */
      args[0]
    );
    event2.stopPropagation();
    return fn?.apply(this, args);
  };
}
function preventDefault(fn) {
  return function(...args) {
    var event2 = (
      /** @type {Event} */
      args[0]
    );
    event2.preventDefault();
    return fn?.apply(this, args);
  };
}

// node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function init(immutable = false) {
  const context = (
    /** @type {ComponentContextLegacy} */
    component_context
  );
  const callbacks = context.l.u;
  if (!callbacks) return;
  let props = () => deep_read_state(context.s);
  if (immutable) {
    let version = 0;
    let prev = (
      /** @type {Record<string, any>} */
      {}
    );
    const d = derived(() => {
      let changed = false;
      const props2 = context.s;
      for (const key2 in props2) {
        if (props2[key2] !== prev[key2]) {
          prev[key2] = props2[key2];
          changed = true;
        }
      }
      if (changed) version++;
      return version;
    });
    props = () => get(d);
  }
  if (callbacks.b.length) {
    user_pre_effect(() => {
      observe_all(context, props);
      run_all(callbacks.b);
    });
  }
  user_effect(() => {
    const fns = untrack(() => callbacks.m.map(run));
    return () => {
      for (const fn of fns) {
        if (typeof fn === "function") {
          fn();
        }
      }
    };
  });
  if (callbacks.a.length) {
    user_effect(() => {
      observe_all(context, props);
      run_all(callbacks.a);
    });
  }
}
function observe_all(context, props) {
  if (context.l.s) {
    for (const signal of context.l.s) get(signal);
  }
  props();
}

// node_modules/svelte/src/internal/client/reactivity/store.js
var is_store_binding = false;
var IS_UNMOUNTED = Symbol("unmounted");
function capture_store_binding(fn) {
  var previous_is_store_binding = is_store_binding;
  try {
    is_store_binding = false;
    return [fn(), is_store_binding];
  } finally {
    is_store_binding = previous_is_store_binding;
  }
}

// node_modules/svelte/src/internal/client/reactivity/props.js
function prop(props, key2, flags2, fallback2) {
  var runes = !legacy_mode_flag || (flags2 & PROPS_IS_RUNES) !== 0;
  var bindable = (flags2 & PROPS_IS_BINDABLE) !== 0;
  var lazy = (flags2 & PROPS_IS_LAZY_INITIAL) !== 0;
  var fallback_value = (
    /** @type {V} */
    fallback2
  );
  var fallback_dirty = true;
  var fallback_signal = (
    /** @type {Derived<V> | undefined} */
    void 0
  );
  var get_fallback = () => {
    if (lazy && runes) {
      fallback_signal ??= derived(
        /** @type {() => V} */
        fallback2
      );
      return get(fallback_signal);
    }
    if (fallback_dirty) {
      fallback_dirty = false;
      fallback_value = lazy ? untrack(
        /** @type {() => V} */
        fallback2
      ) : (
        /** @type {V} */
        fallback2
      );
    }
    return fallback_value;
  };
  let setter;
  if (bindable) {
    var is_entry_props = STATE_SYMBOL in props || LEGACY_PROPS in props;
    setter = get_descriptor(props, key2)?.set ?? (is_entry_props && key2 in props ? (v) => props[key2] = v : void 0);
  }
  var initial_value;
  var is_store_sub = false;
  if (bindable) {
    [initial_value, is_store_sub] = capture_store_binding(() => (
      /** @type {V} */
      props[key2]
    ));
  } else {
    initial_value = /** @type {V} */
    props[key2];
  }
  if (initial_value === void 0 && fallback2 !== void 0) {
    initial_value = get_fallback();
    if (setter) {
      if (runes) props_invalid_value(key2);
      setter(initial_value);
    }
  }
  var getter;
  if (runes) {
    getter = () => {
      var value = (
        /** @type {V} */
        props[key2]
      );
      if (value === void 0) return get_fallback();
      fallback_dirty = true;
      return value;
    };
  } else {
    getter = () => {
      var value = (
        /** @type {V} */
        props[key2]
      );
      if (value !== void 0) {
        fallback_value = /** @type {V} */
        void 0;
      }
      return value === void 0 ? fallback_value : value;
    };
  }
  if (runes && (flags2 & PROPS_IS_UPDATED) === 0) {
    return getter;
  }
  if (setter) {
    var legacy_parent = props.$$legacy;
    return (
      /** @type {() => V} */
      (function(value, mutation) {
        if (arguments.length > 0) {
          if (!runes || !mutation || legacy_parent || is_store_sub) {
            setter(mutation ? getter() : value);
          }
          return value;
        }
        return getter();
      })
    );
  }
  var overridden = false;
  var d = ((flags2 & PROPS_IS_IMMUTABLE) !== 0 ? derived : derived_safe_equal)(() => {
    overridden = false;
    return getter();
  });
  if (dev_fallback_default) {
    d.label = key2;
  }
  if (bindable) get(d);
  var parent_effect = (
    /** @type {Effect} */
    active_effect
  );
  return (
    /** @type {() => V} */
    (function(value, mutation) {
      if (arguments.length > 0) {
        const new_value = mutation ? get(d) : runes && bindable ? proxy(value) : value;
        set(d, new_value);
        overridden = true;
        if (fallback_value !== void 0) {
          fallback_value = new_value;
        }
        return value;
      }
      if (is_destroying_effect && overridden || (parent_effect.f & DESTROYED) !== 0) {
        return d.v;
      }
      return get(d);
    })
  );
}

// node_modules/svelte/src/legacy/legacy-client.js
function createClassComponent(options) {
  return new Svelte4Component(options);
}
var Svelte4Component = class {
  /** @type {any} */
  #events;
  /** @type {Record<string, any>} */
  #instance;
  /**
   * @param {ComponentConstructorOptions & {
   *  component: any;
   * }} options
   */
  constructor(options) {
    var sources = /* @__PURE__ */ new Map();
    var add_source = (key2, value) => {
      var s = mutable_source(value, false, false);
      sources.set(key2, s);
      return s;
    };
    const props = new Proxy(
      { ...options.props || {}, $$events: {} },
      {
        get(target, prop2) {
          return get(sources.get(prop2) ?? add_source(prop2, Reflect.get(target, prop2)));
        },
        has(target, prop2) {
          if (prop2 === LEGACY_PROPS) return true;
          get(sources.get(prop2) ?? add_source(prop2, Reflect.get(target, prop2)));
          return Reflect.has(target, prop2);
        },
        set(target, prop2, value) {
          set(sources.get(prop2) ?? add_source(prop2, value), value);
          return Reflect.set(target, prop2, value);
        }
      }
    );
    this.#instance = (options.hydrate ? hydrate : mount)(options.component, {
      target: options.target,
      anchor: options.anchor,
      props,
      context: options.context,
      intro: options.intro ?? false,
      recover: options.recover,
      transformError: options.transformError
    });
    if (!async_mode_flag && (!options?.props?.$$host || options.sync === false)) {
      flushSync();
    }
    this.#events = props.$$events;
    for (const key2 of Object.keys(this.#instance)) {
      if (key2 === "$set" || key2 === "$destroy" || key2 === "$on") continue;
      define_property(this, key2, {
        get() {
          return this.#instance[key2];
        },
        /** @param {any} value */
        set(value) {
          this.#instance[key2] = value;
        },
        enumerable: true
      });
    }
    this.#instance.$set = /** @param {Record<string, any>} next */
    (next2) => {
      Object.assign(props, next2);
    };
    this.#instance.$destroy = () => {
      unmount(this.#instance);
    };
  }
  /** @param {Record<string, any>} props */
  $set(props) {
    this.#instance.$set(props);
  }
  /**
   * @param {string} event
   * @param {(...args: any[]) => any} callback
   * @returns {any}
   */
  $on(event2, callback) {
    this.#events[event2] = this.#events[event2] || [];
    const cb = (...args) => callback.call(this, ...args);
    this.#events[event2].push(cb);
    return () => {
      this.#events[event2] = this.#events[event2].filter(
        /** @param {any} fn */
        (fn) => fn !== cb
      );
    };
  }
  $destroy() {
    this.#instance.$destroy();
  }
};

// node_modules/svelte/src/internal/client/dom/elements/custom-element.js
var SvelteElement;
if (typeof HTMLElement === "function") {
  SvelteElement = class extends HTMLElement {
    /** The Svelte component constructor */
    $$ctor;
    /** Slots */
    $$s;
    /** @type {any} The Svelte component instance */
    $$c;
    /** Whether or not the custom element is connected */
    $$cn = false;
    /** @type {Record<string, any>} Component props data */
    $$d = {};
    /** `true` if currently in the process of reflecting component props back to attributes */
    $$r = false;
    /** @type {Record<string, CustomElementPropDefinition>} Props definition (name, reflected, type etc) */
    $$p_d = {};
    /** @type {Record<string, EventListenerOrEventListenerObject[]>} Event listeners */
    $$l = {};
    /** @type {Map<EventListenerOrEventListenerObject, Function>} Event listener unsubscribe functions */
    $$l_u = /* @__PURE__ */ new Map();
    /** @type {any} The managed render effect for reflecting attributes */
    $$me;
    /** @type {ShadowRoot | null} The ShadowRoot of the custom element */
    $$shadowRoot = null;
    /**
     * @param {*} $$componentCtor
     * @param {*} $$slots
     * @param {ShadowRootInit | undefined} shadow_root_init
     */
    constructor($$componentCtor, $$slots, shadow_root_init) {
      super();
      this.$$ctor = $$componentCtor;
      this.$$s = $$slots;
      if (shadow_root_init) {
        this.$$shadowRoot = this.attachShadow(shadow_root_init);
      }
    }
    /**
     * @param {string} type
     * @param {EventListenerOrEventListenerObject} listener
     * @param {boolean | AddEventListenerOptions} [options]
     */
    addEventListener(type, listener, options) {
      this.$$l[type] = this.$$l[type] || [];
      this.$$l[type].push(listener);
      if (this.$$c) {
        const unsub = this.$$c.$on(type, listener);
        this.$$l_u.set(listener, unsub);
      }
      super.addEventListener(type, listener, options);
    }
    /**
     * @param {string} type
     * @param {EventListenerOrEventListenerObject} listener
     * @param {boolean | AddEventListenerOptions} [options]
     */
    removeEventListener(type, listener, options) {
      super.removeEventListener(type, listener, options);
      if (this.$$c) {
        const unsub = this.$$l_u.get(listener);
        if (unsub) {
          unsub();
          this.$$l_u.delete(listener);
        }
      }
    }
    async connectedCallback() {
      this.$$cn = true;
      if (!this.$$c) {
        let create_slot = function(name) {
          return (anchor) => {
            const slot2 = create_element("slot");
            if (name !== "default") slot2.name = name;
            append(anchor, slot2);
          };
        };
        await Promise.resolve();
        if (!this.$$cn || this.$$c) {
          return;
        }
        const $$slots = {};
        const existing_slots = get_custom_elements_slots(this);
        for (const name of this.$$s) {
          if (name in existing_slots) {
            if (name === "default" && !this.$$d.children) {
              this.$$d.children = create_slot(name);
              $$slots.default = true;
            } else {
              $$slots[name] = create_slot(name);
            }
          }
        }
        for (const attribute of this.attributes) {
          const name = this.$$g_p(attribute.name);
          if (!(name in this.$$d)) {
            this.$$d[name] = get_custom_element_value(name, attribute.value, this.$$p_d, "toProp");
          }
        }
        for (const key2 in this.$$p_d) {
          if (!(key2 in this.$$d) && this[key2] !== void 0) {
            this.$$d[key2] = this[key2];
            delete this[key2];
          }
        }
        this.$$c = createClassComponent({
          component: this.$$ctor,
          target: this.$$shadowRoot || this,
          props: {
            ...this.$$d,
            $$slots,
            $$host: this
          }
        });
        this.$$me = effect_root(() => {
          render_effect(() => {
            this.$$r = true;
            for (const key2 of object_keys(this.$$c)) {
              if (!this.$$p_d[key2]?.reflect) continue;
              this.$$d[key2] = this.$$c[key2];
              const attribute_value = get_custom_element_value(
                key2,
                this.$$d[key2],
                this.$$p_d,
                "toAttribute"
              );
              if (attribute_value == null) {
                this.removeAttribute(this.$$p_d[key2].attribute || key2);
              } else {
                this.setAttribute(this.$$p_d[key2].attribute || key2, attribute_value);
              }
            }
            this.$$r = false;
          });
        });
        for (const type in this.$$l) {
          for (const listener of this.$$l[type]) {
            const unsub = this.$$c.$on(type, listener);
            this.$$l_u.set(listener, unsub);
          }
        }
        this.$$l = {};
      }
    }
    // We don't need this when working within Svelte code, but for compatibility of people using this outside of Svelte
    // and setting attributes through setAttribute etc, this is helpful
    /**
     * @param {string} attr
     * @param {string} _oldValue
     * @param {string} newValue
     */
    attributeChangedCallback(attr2, _oldValue, newValue) {
      if (this.$$r) return;
      attr2 = this.$$g_p(attr2);
      this.$$d[attr2] = get_custom_element_value(attr2, newValue, this.$$p_d, "toProp");
      this.$$c?.$set({ [attr2]: this.$$d[attr2] });
    }
    disconnectedCallback() {
      this.$$cn = false;
      Promise.resolve().then(() => {
        if (!this.$$cn && this.$$c) {
          this.$$c.$destroy();
          this.$$me();
          this.$$c = void 0;
        }
      });
    }
    /**
     * @param {string} attribute_name
     */
    $$g_p(attribute_name) {
      return object_keys(this.$$p_d).find(
        (key2) => this.$$p_d[key2].attribute === attribute_name || !this.$$p_d[key2].attribute && key2.toLowerCase() === attribute_name
      ) || attribute_name;
    }
  };
}
function get_custom_element_value(prop2, value, props_definition, transform) {
  const type = props_definition[prop2]?.type;
  value = type === "Boolean" && typeof value !== "boolean" ? value != null : value;
  if (!transform || !props_definition[prop2]) {
    return value;
  } else if (transform === "toAttribute") {
    switch (type) {
      case "Object":
      case "Array":
        return value == null ? null : JSON.stringify(value);
      case "Boolean":
        return value ? "" : null;
      case "Number":
        return value == null ? null : value;
      default:
        return value;
    }
  } else {
    switch (type) {
      case "Object":
      case "Array":
        return value && JSON.parse(value);
      case "Boolean":
        return value;
      // conversion already handled above
      case "Number":
        return value != null ? +value : value;
      default:
        return value;
    }
  }
}
function get_custom_elements_slots(element2) {
  const result = {};
  element2.childNodes.forEach((node) => {
    result[
      /** @type {Element} node */
      node.slot || "default"
    ] = true;
  });
  return result;
}

// node_modules/svelte/src/index-client.js
if (dev_fallback_default) {
  let throw_rune_error = function(rune) {
    if (!(rune in globalThis)) {
      let value;
      Object.defineProperty(globalThis, rune, {
        configurable: true,
        // eslint-disable-next-line getter-return
        get: () => {
          if (value !== void 0) {
            return value;
          }
          rune_outside_svelte(rune);
        },
        set: (v) => {
          value = v;
        }
      });
    }
  };
  throw_rune_error("$state");
  throw_rune_error("$effect");
  throw_rune_error("$derived");
  throw_rune_error("$inspect");
  throw_rune_error("$props");
  throw_rune_error("$bindable");
}
function onMount(fn) {
  if (component_context === null) {
    lifecycle_outside_component("onMount");
  }
  if (legacy_mode_flag && component_context.l !== null) {
    init_update_callbacks(component_context).m.push(fn);
  } else {
    user_effect(() => {
      const cleanup = untrack(fn);
      if (typeof cleanup === "function") return (
        /** @type {() => void} */
        cleanup
      );
    });
  }
}
function init_update_callbacks(context) {
  var l = (
    /** @type {ComponentContextLegacy} */
    context.l
  );
  return l.u ??= { a: [], b: [], m: [] };
}

// node_modules/svelte/src/version.js
var PUBLIC_VERSION = "5";

// node_modules/svelte/src/internal/disclose-version.js
if (typeof window !== "undefined") {
  ((window.__svelte ??= {}).v ??= /* @__PURE__ */ new Set()).add(PUBLIC_VERSION);
}

// node_modules/svelte/src/internal/flags/legacy.js
enable_legacy_mode_flag();

// src/world-path.json
var world_path_default = "M895.311,268.764L895.932,268.349L896.796,269.073L896.382,270.376L894.834,270.719L893.457,270.41L893.214,269.31L894.177,268.451ZM900,266.39L898.407,267.004L896.814,267.528L896.49,266.597L897.741,266.085L898.533,265.946L900,265.167L900,265.167L900,266.39ZM0,265.167L0,265.167L0,265.167L0.513,265.053L0.207,266.255L0,266.39L0,266.39L0,265.167ZM534.758,227.377L535.181,227.652L544.244,232.742L544.415,234.193L548.006,236.69L546.854,239.77L546.998,241.188L548.6,242.102L548.672,242.749L547.988,244.26L548.132,245.022L547.97,246.215L548.843,247.78L549.878,250.247L550.788,250.793L548.798,252.24L546.071,253.214L544.568,253.171L543.677,253.92L541.94,253.988L541.283,254.301L538.277,253.599L536.396,253.802L535.703,250.4L534.848,249.236L534.353,248.542L531.896,248.077L530.483,247.328L528.89,246.904L527.891,246.486L526.847,245.851L525.497,242.698L524.048,241.302L523.553,239.851L523.796,238.552L523.346,236.25L524.381,236.131L525.29,235.226L526.262,233.923L526.883,233.398L526.856,232.585L526.316,232.018L526.172,231.033L526.892,230.719L527.036,229.247L526.046,227.838L526.928,227.537L529.664,227.567ZM428.332,155.858L428.341,156.027L428.287,156.509L428.278,160.296L420.079,160.165L420.16,166.563L417.811,166.787L417.199,168.074L417.676,171.683L407.884,171.666L407.344,172.5L407.452,171.446L407.497,171.45L413.122,171.247L413.419,170.346L414.445,169.225L415.273,165.772L418.747,163.076L419.926,159.924L420.7,159.738L421.519,157.791L423.625,157.525L424.525,157.846L425.659,157.846L426.469,157.279L428.017,157.199L427.954,155.858ZM142.903,102.5L142.561,102.495L137.728,100.037L135.937,98.958L131.41,97.925L130.015,95.712L130.375,94.176L127.171,93.11L126.739,91.096L123.715,89.281L123.661,87.994L125.047,86.788L124.984,85.21L120.727,83.619L118.171,80.767L116.614,78.973L114.319,77.848L112.636,76.824L111.313,75.529L108.802,76.341L106.372,77.737L104.149,76.096L102.403,75L99.964,74.306L97.507,74.234L97.516,59.999L97.534,50.72L102.196,51.321L106.138,52.527L108.739,52.755L110.935,51.71L113.959,50.932L117.676,51.236L121.42,50.14L125.515,49.514L127.234,50.551L129.097,49.967L129.655,48.791L131.383,49.057L135.613,51.3L138.934,49.603L139.276,51.503L142.345,51.092L143.29,50.36L146.323,50.504L150.14,51.554L155.99,52.472L159.437,52.895L161.885,52.734L165.251,54.004L161.741,55.243L166.259,55.781L173.009,55.485L175.133,55.049L177.797,56.547L180.515,55.281L177.968,54.219L179.579,53.365L182.621,53.25L184.628,53.001L186.644,53.597L189.155,54.956L191.945,54.757L196.364,55.882L200.243,55.485L203.888,55.544L203.6,53.991L205.823,53.555L209.702,54.401L209.684,56.767L211.277,54.774L213.284,54.841L214.418,52.328L211.736,50.788L208.82,49.776L209.018,47.013L211.979,45.198L215.273,45.6L217.802,46.704L221.204,49.523L218.981,50.75L223.634,51.257L223.625,53.813L226.964,51.854L229.952,53.462L229.205,55.315L231.626,57.004L234.236,55.197L236.054,53.039L236.198,50.293L239.744,50.487L243.443,50.855L246.8,52.095L246.953,53.335L245.09,54.668L246.854,56.005L246.53,57.224L241.634,58.971L238.16,59.356L235.577,58.603L234.83,59.86L232.418,61.967L231.689,63.063L228.791,64.751L225.218,64.916L223.238,65.974L223.076,67.599L220.169,67.912L217.109,69.939L214.4,72.753L213.428,74.725L213.284,77.627L216.965,78.046L218.09,80.386L219.26,82.282L222.752,81.787L227.405,82.87L229.898,83.822L231.689,85.003L234.821,85.693L237.467,86.742L241.598,86.886L244.316,87.131L243.911,89.293L244.685,91.807L246.494,94.604L250.221,96.978L252.147,96.165L253.497,93.597L252.192,89.645L250.428,88.329L254.433,87.161L257.259,85.405L258.645,83.666L258.438,81.994L256.746,79.87L253.704,77.987L256.656,75.368L255.567,73.104L254.73,69.203L256.476,68.623L260.76,69.304L263.334,69.546L265.404,68.89L267.726,69.736L270.804,71.187L271.569,72.156L276.024,72.347L275.952,74.445L276.78,77.606L279.066,77.996L280.875,79.468L284.493,78.08L286.887,75.321L288.543,74.162L290.487,76.392L293.745,79.582L296.508,82.582L295.5,84.152L298.83,85.561L301.08,86.992L305.058,87.635L306.669,88.434L307.659,90.55L309.603,90.88L310.611,91.824L310.791,94.633L308.973,95.573L307.182,96.449L303.06,97.337L299.919,99.394L295.689,99.8L290.343,99.271L286.59,99.254L284.007,99.428L281.91,101.222L278.724,102.33L275.115,105.639L272.235,107.945L274.359,107.535L278.373,104.251L283.62,102.165L287.355,101.92L289.569,103.143L287.211,104.823L288.003,107.518L288.822,109.405L292.071,110.654L296.202,110.29L298.704,107.48L298.875,109.295L300.495,110.201L297.399,111.838L291.864,113.324L289.38,114.335L286.59,116.137L284.691,115.951L284.592,113.836L288.939,111.771L284.934,111.851L282.153,112.156L280.524,110.742L280.524,107.336L279.417,106.613L277.734,107.036L276.906,106.38L274.998,108.267L274.242,110.213L273.351,111.352L272.289,111.737L271.488,111.864L271.236,112.481L266.628,112.481L262.83,112.498L261.705,112.96L259.059,114.758L258.753,114.953L257.952,115.93L255.657,115.926L253.2,115.939L252.075,116.332L252.471,116.823L252.696,117.589L252.651,117.843L249.383,119.082L246.809,119.476L243.902,120.813L243.272,120.813L242.426,120.42L242.147,120.06L242.201,119.802L242.75,118.926L243.929,117.551L244.658,116.074L244.154,113.899L243.623,111.631L241.013,110.459L241.328,110.015L240.959,109.706L240.275,109.706L239.771,109.312L239.645,108.72L239.159,108.978L238.484,108.902L238.637,108.652L238.052,108.407L237.809,107.751L235.865,106.951L233.849,106.117L231.401,105.148L229.052,104.243L226.82,104.95L226.001,104.975L222.923,104.323L220.898,104.649L218.477,103.875L215.921,103.477L214.175,103.325L213.401,102.902L212.96,101.526L212.114,101.539L212.105,102.5L206.93,102.5L198.371,102.5L189.875,102.5L182.378,102.5L174.872,102.5L167.501,102.5L159.878,102.5L157.421,102.5L150.005,102.5ZM240.014,68.868L241.877,67.713L245.306,67.739L245.252,68.221L242.327,69.601L240.563,69.546ZM250.563,42.994L247.808,41.669L247.916,40.768L249.113,40.603L254.838,40.869L259.149,42.245L259.374,42.934L256.71,42.862L254.019,42.807L251.283,43.146ZM249.212,69.787L250.176,69.038L251.202,69.093L251.832,69.605L250.86,70.916L249.752,70.705L249.095,69.96ZM215.966,37.552L214.607,38.521L210.98,38.335L207.947,37.679L209.279,36.553L212.87,35.881L215.057,36.761ZM215.399,31.201L214.265,31.273L209.576,31.112L208.91,30.414L213.941,30.452L215.696,30.913ZM208.118,28.086L211.106,28.954L210.422,29.859L206.723,30.375L204.689,29.792L203.618,28.856L203.42,27.82L206.66,27.921ZM229.628,39.02L225.587,38.711L218.945,37.907L218.081,36.532L217.775,35.292L215.264,34.201L210.098,33.896L207.2,33.122L208.136,32.098L213.293,32.254L216.065,33.058L220.988,33.054L223.148,33.875L222.572,34.814L225.443,35.381L227.036,35.974L230.402,36.084L234.056,36.295L238.025,35.754L243.119,35.538L247.178,35.715L249.86,36.659L250.419,37.692L248.852,38.356L245.126,38.893L241.931,38.589L234.758,38.974ZM171.839,29.618L175.367,30.007L174.53,30.756L169.868,31.476L166.169,30.667L168.185,29.872ZM172.595,27.989L175.844,28.497L172.793,28.983L168.644,28.979L168.689,28.624L171.254,27.875ZM310.998,96.707L309.666,98.281L308.01,100.469L309.639,99.627L311.322,100.16L310.44,101.031L312.663,101.717L313.815,101.108L316.308,101.878L315.534,103.71L317.28,103.282L317.604,104.607L318.378,106.16L317.325,108.36L316.2,108.453L314.553,107.984L315.093,105.936L314.4,105.618L311.502,107.789L310.008,107.7L311.772,106.528L309.369,105.919L306.687,106.067L301.836,105.991L301.449,105.25L303.006,104.37L301.917,103.693L304.023,102.187L306.606,98.205L308.154,96.783L310.323,95.92L311.484,96.03ZM240.293,62.225L243.029,63.084L245.891,63.863L246.116,65.052L247.952,64.857L249.743,65.686L247.52,66.474L243.632,65.873L242.228,64.747L239.753,66.076L236.189,67.371L235.334,65.907L231.941,66.148L234.119,64.912L234.434,62.945L235.289,60.651L237.098,60.858L237.557,61.954L238.844,61.569ZM253.074,44.119L255.441,43.125L260.985,44.39L264.432,45.583L264.756,46.675L269.391,46.108L272.001,47.699L278.031,48.689L280.209,49.696L282.576,52.036L277.986,53.2L283.872,54.833L287.841,55.383L291.441,57.681L295.374,57.846L294.591,59.598L290.208,62.504L287.13,61.434L283.197,59.03L279.966,59.344L279.651,60.774L282.279,62.229L285.672,63.38L286.698,64.045L288.327,66.516L287.463,68.314L284.313,67.637L278.04,65.636L281.577,67.789L284.178,69.3L284.583,70.172L277.806,69.173L272.442,67.722L269.409,66.507L270.282,65.801L266.556,64.514L262.911,63.304L262.956,64.028L255.729,64.426L253.614,63.567L255.261,61.726L259.959,61.684L265.098,61.362L264.27,60.469L265.134,59.225L268.374,56.788L267.681,55.683L266.718,54.824L262.893,53.614L257.826,52.764L259.428,52.129L256.782,50.576L254.577,50.432L252.606,49.582L251.265,50.322L246.737,50.644L237.638,50.085L232.346,49.349L228.296,48.972L226.217,48.097L228.827,46.954L225.281,46.946L224.489,44.411L226.406,42.177L228.98,41.157L235.433,40.489L233.597,42.105L235.568,43.666L237.872,41.648L244.208,40.624L248.501,43.209L248.123,44.847ZM213.743,39.663L218.954,39.748L223.724,40.357L219.989,42.583L217.01,43.07L214.328,44.94L211.475,44.847L209.918,42.651L209.954,41.407L211.259,40.345ZM142.858,34.708L147.106,32.838L152.237,31.218L156.071,31.256L159.5,30.887L159.158,32.809L157.232,33.676L154.901,33.799L150.248,34.865L146.251,35.25ZM118.225,89.899L120.628,89.7L119.872,92.539L122.05,94.549L121.051,94.545L119.548,93.402L118.621,92.251L117.361,91.473L116.902,90.372L117.046,89.577ZM186.266,26.745L191.18,27.088L197.939,27.997L199.847,29.186L200.819,30.232L196.742,29.952L192.629,29.14L187.058,29.051L189.47,28.306L186.455,27.705ZM141.229,103.727L139.969,104.074L135.865,102.935L135.109,102.051L132.877,101.175L132.427,100.464L129.853,100.012L128.89,98.653L129.106,98.074L131.725,98.619L133.264,98.996L135.613,99.263L136.459,100.126L137.701,101.311L140.194,102.343ZM146.152,38.876L149.725,39.397L156.107,39.536L158.537,40.26L161.219,41.314L158.078,41.944L151.949,43.7L148.852,45.452L148.852,46.539L142.273,47.745L140.95,46.649L135.181,45.329L136.252,44.271L137.98,42.443L140.149,40.802L137.701,39.27ZM180.452,35.385L182.675,34.967L185.294,35.077L185.735,36.299L184.214,37.488L175.754,37.874L169.445,38.957L165.638,39.016L165.323,38.199L170.516,37.095L159.221,37.391L155.72,36.943L159.131,34.501L161.489,33.803L168.527,34.645L172.964,36.126L177.329,36.316L173.756,33.926L176.051,33.016L178.625,33.304L179.471,34.497ZM183.692,42.308L186.491,43.319L188.066,45.752L188.84,47.517L193.034,48.757L197.552,49.937L197.273,51.037L193.169,51.24L194.771,52.201L193.925,53.119L189.398,52.726L185.096,52.049L182.198,52.201L177.5,53.052L171.164,53.424L166.718,53.661L165.359,52.48L161.948,51.799L159.734,52.078L156.647,50.098L158.312,49.836L162.173,49.408L165.701,49.518L168.959,49.082L164.126,48.499L158.78,48.697L155.234,48.647L153.92,47.728L159.716,46.726L155.864,46.764L151.499,46.104L153.596,44.229L155.333,43.235L162.029,41.716L164.585,42.198L163.334,43.37L168.896,42.613L172.37,43.874L175.196,42.596L177.482,43.417L179.525,45.871L180.785,44.838L179.012,42.274L181.208,41.91ZM198.902,43.235L196.148,41.601L199.109,40.391L202.088,40.916L206.552,40.599L207.2,41.326L204.869,42.524L208.649,43.599L208.199,45.85L204.104,46.819L201.692,46.607L199.964,45.655L193.754,43.726L193.799,42.926ZM183.503,41.001L186.851,40.899L188.75,41.449L186.554,43.099L182.648,41.352ZM203.753,33.202L205.661,34.357L205.742,35.639L204.599,37.501L200.477,37.755L197.795,37.357L197.84,35.897L193.745,36.092L193.583,34.158L196.274,34.235L200.045,33.384L203.555,33.528ZM209.963,23.495L211.691,22.734L214.256,22.556L213.158,21.985L218.972,21.858L222.167,23.191L226.379,23.728L230.474,24.202L232.454,25.852L235.46,26.656L232.031,27.401L227.414,29.284L222.986,29.461L217.811,29.14L215.12,28.124L215.156,27.215L217.136,26.55L212.564,26.567L209.81,25.738L208.226,24.604ZM221.033,20.262L224.75,19.789L227.666,19.708L232.571,19.302L236.252,18.371L239.348,18.498L242.048,19.2L243.947,17.851L247.25,17.449L251.733,17.174L259.374,17.072L260.706,17.339L267.924,16.915L273.333,17.076L278.751,17.233L285.429,17.432L290.802,17.749L295.374,18.43L295.266,19.095L289.164,20.182L283.116,20.686L280.857,21.248L286.302,21.236L280.398,22.751L276.33,23.457L272.046,25.501L266.889,25.916L265.296,26.423L257.727,26.694L261.174,27.007L259.446,27.452L261.516,28.687L259.14,29.542L255.279,30.249L254.091,31.23L250.599,31.975L250.95,32.542L255.225,32.445L255.279,33.054L248.6,34.556L242.066,33.866L234.722,34.251L230.996,33.951L226.271,33.82L225.956,32.618L230.582,32.055L229.349,30.249L230.879,30.075L237.557,31.154L234.146,29.55L230.096,29.072L232.121,28.103L236.549,27.507L237.26,26.635L233.732,25.657L232.67,24.371L239.501,24.481L241.481,24.752L245.378,23.838L239.753,23.55L231.005,23.711L226.586,22.861L224.498,21.849L221.582,21.117ZM261.957,56.39L260.337,57.126L257.529,57.253L256.908,56.03L257.97,54.63L260.265,54.283L262.218,54.973L262.245,56.043ZM209.36,51.274L210.881,52.231L209.324,53.107L205.958,52.349L203.924,52.624L200.504,51.499L202.709,50.724L204.455,49.641L207.11,50.352L208.604,50.8ZM288.705,100.316L289.569,100.109L292.854,100.735L295.41,101.78L295.482,102.237L294.267,102.284L291.027,101.497ZM289.965,107.408L290.838,108.627L292.656,108.961L294.969,108.893L293.736,109.917L292.818,110.078L289.641,109.02L289.02,108.182ZM142.903,102.5L150.005,102.5L157.421,102.5L159.878,102.5L167.501,102.5L174.872,102.5L182.378,102.5L189.875,102.5L198.371,102.5L206.93,102.5L212.105,102.5L212.114,101.539L212.96,101.526L213.401,102.902L214.175,103.325L215.921,103.477L218.477,103.875L220.898,104.649L222.923,104.323L226.001,104.975L226.82,104.95L229.052,104.243L231.401,105.148L233.849,106.117L235.865,106.951L237.809,107.751L238.052,108.407L238.637,108.652L238.484,108.902L239.159,108.978L239.645,108.72L239.771,109.312L240.275,109.706L240.959,109.706L241.328,110.015L241.013,110.459L243.623,111.631L244.154,113.899L244.658,116.074L243.929,117.551L242.75,118.926L242.201,119.802L242.147,120.06L242.426,120.42L243.272,120.813L243.902,120.813L246.809,119.476L249.383,119.082L252.651,117.843L252.696,117.589L252.471,116.823L252.075,116.332L253.2,115.939L255.657,115.926L257.952,115.93L258.753,114.953L259.059,114.758L261.705,112.96L262.83,112.498L266.628,112.481L271.236,112.481L271.488,111.864L272.289,111.737L273.351,111.352L274.242,110.213L274.998,108.267L276.906,106.38L277.734,107.036L279.417,106.613L280.524,107.336L280.524,110.742L282.153,112.156L282.585,112.977L279.921,114.187L277.347,115.05L274.71,115.79L273.387,117.276L272.964,117.838L272.937,119.163L273.765,120.487L274.8,120.551L274.539,119.637L275.286,120.191L275.088,120.906L273.396,121.312L272.199,121.266L270.354,121.702L269.265,121.824L267.807,121.947L265.728,122.671L269.4,122.201L270.138,122.675L266.637,123.424L265.044,123.428L265.116,123.123L264.36,123.817L265.098,123.932L264.558,125.726L262.731,127.651L262.551,127.008L262.002,126.881L261.183,126.255L261.696,127.6L262.317,128.045L262.362,128.988L261.561,129.961L260.148,131.959L259.923,131.857L260.697,130.156L259.419,129.204L259.122,127.126L258.645,128.205L259.176,129.792L257.529,129.399L259.248,130.207L259.356,132.585L260.067,132.758L260.328,133.622L260.679,136.122L259.095,137.98L256.503,138.72L254.865,140.184L253.614,140.345L252.345,141.263L251.994,142.106L249.248,143.726L247.835,144.915L246.656,146.4L246.269,148.173L246.719,149.912L247.547,152.049L248.663,153.818L248.672,154.901L249.86,157.8L249.779,159.484L249.671,160.457L249.05,161.985L248.303,162.302L247.07,161.997L246.674,160.901L245.729,160.326L244.397,158.176L243.236,156.264L242.858,155.286L243.371,153.623L242.678,152.248L240.725,150.158L239.753,149.777L237.224,150.911L236.783,150.784L235.568,149.62L234.002,148.998L231.176,149.316L228.953,149.037L227.045,149.21L226.019,149.599L226.469,150.264L226.424,151.279L226.955,151.774L226.478,152.1L225.551,151.732L224.615,152.206L222.797,152.13L220.934,150.809L218.756,151.118L216.938,150.539L215.381,150.716L213.275,151.3L210.998,153.154L208.514,154.233L207.146,155.426L206.579,156.551L206.552,158.274L206.678,159.475L207.146,160.326L206.174,160.402L204.401,159.852L202.448,159.073L201.746,157.901L201.197,156.15L199.721,154.724L198.857,153.259L197.606,151.55L195.842,150.551L193.799,150.598L192.224,152.574L190.154,151.825L188.858,151.072L188.237,149.697L187.409,148.389L185.924,147.289L184.646,146.502L183.728,145.613L179.399,145.613L179.399,146.646L177.41,146.646L172.442,146.663L166.736,144.902L162.965,143.688L163.199,143.197L160.022,143.468L157.178,143.663L156.764,142.385L155.144,140.946L153.974,140.646L153.704,139.931L152.3,139.804L151.4,139.131L149.077,138.881L148.438,138.479L148.141,137.108L145.711,134.595L143.632,131.121L143.722,130.541L142.615,129.716L140.68,127.621L140.338,125.582L139.006,124.215L139.555,122.146L139.465,120.001L138.664,118.084L139.645,115.727L139.951,113.459L140.248,111.191L139.798,107.84L139.006,105.699L138.286,104.539L138.583,104.053L142.201,104.899L143.533,107.26L144.154,106.6L143.749,104.552ZM61.498,174.802L61.939,175.017L62.344,175.352L62.983,176.227L62.92,176.367L61.948,176.9L61.147,177.29L60.778,177.708L60.157,177.353L60.229,176.655L59.815,175.741L59.941,175.466L60.373,175.055L60.202,174.565L60.346,174.332L60.535,174.378ZM60.013,173.088L59.806,173.388L58.96,173.57L58.537,173.041L58.249,172.838L58.222,172.682L58.465,172.47L59.356,172.707ZM58.105,172.06L58.024,172.326L56.683,172.254L56.872,171.95ZM54.937,170.706L55.144,170.866L55.864,171.696L55.729,171.84L55.558,171.806L54.685,171.717L54.37,171.154L54.271,171.052ZM51.589,169.461L51.634,170.045L51.337,170.291L50.5,169.838L50.626,169.656L51.013,169.411ZM33.831,74.039L35.811,74.268L36.054,75.224L34.515,75.613L32.877,75.148L31.365,74.467ZM66.925,80.077L68.59,80.247L69.643,81.021L67.483,82.21L64.99,83.162L63.712,82.519L63.325,81.347L65.593,80.458ZM97.534,50.72L97.516,59.999L97.507,74.234L99.964,74.306L102.403,75L104.149,76.096L106.372,77.737L108.802,76.341L111.313,75.529L112.636,76.824L114.319,77.848L116.614,78.973L118.171,80.767L120.727,83.619L124.984,85.21L125.047,86.788L123.661,87.994L122.284,87.051L120.079,86.255L119.377,84.076L116.155,82.054L114.805,79.692L112.402,79.532L108.433,79.468L105.499,78.749L100.333,76.155L97.939,75.681L93.565,74.788L90.1,75.004L85.186,73.853L82.216,72.787L79.435,73.316L79.957,75.055L78.571,75.216L75.682,75.736L73.477,76.578L70.705,77.111L70.354,75.639L71.479,73.185L74.134,72.414L73.45,71.788L70.264,73.18L68.554,74.847L64.954,76.625L66.781,77.839L64.423,79.633L61.732,80.683L59.23,81.444L58.609,82.549L54.703,83.839L53.92,85.015L50.995,86.082L49.275,85.891L46.944,86.59L44.406,87.44L42.327,88.274L38.034,88.989L37.647,88.57L40.383,87.402L42.822,86.632L45.486,85.261L48.591,84.982L49.824,83.953L53.29,82.46L53.848,81.956L55.693,81.076L56.125,79.18L57.394,77.704L54.514,78.461L53.704,78.029L52.354,78.939L50.725,77.67L50.05,78.567L49.113,77.323L46.611,78.321L45.081,78.321L44.865,76.832L45.315,75.918L43.704,75.025L40.455,75.503L38.34,74.331L36.63,73.73L36.621,72.317L34.695,71.251L35.667,69.812L37.701,68.416L38.592,67.134L40.617,66.952L42.336,67.349L44.352,66.143L46.161,66.359L48.069,65.585L47.601,64.442L46.206,63.994L48.051,63.029L46.521,63.059L43.866,63.6L43.101,64.155L41.13,63.6L37.602,63.884L33.939,63.283L32.886,62.276L29.727,60.825L33.237,59.779L38.817,58.557L40.869,58.557L40.527,59.809L45.801,59.712L43.776,58.163L40.698,57.211L38.925,55.958L36.522,54.892L33.093,54.101L34.488,52.793L38.925,52.713L42.075,51.571L42.669,50.356L45.225,49.167L47.664,48.879L52.399,47.771L54.703,47.94L58.546,46.607L62.335,47.132L64.144,48.257L65.251,47.775L69.472,47.923L69.328,48.499L73.153,48.926L75.7,48.676L80.965,49.463L85.771,49.7L87.697,50.026L91.027,49.62L94.816,50.369ZM20.673,65.543L22.212,66.021L23.769,65.763L25.794,66.423L28.278,66.757L28.071,67.028L26.172,67.557L24.273,67.015L23.319,66.562L21.114,66.706L20.52,66.486ZM668.401,101.962L666.493,103.625L664.423,103.862L664.306,106.367L662.911,107.497L657.952,106.676L656.152,111.153L654.865,111.707L649.914,112.706L652.165,117.047L650.455,117.699L650.653,119.125L649.113,118.757L647.853,117.86L644.145,117.597L639.996,117.53L639.096,117.805L635.532,116.755L634.11,117.271L633.723,118.748L629.61,117.885L627.963,118.24L627.405,119.336L625.974,119.798L622.671,121.541L621.582,123.327L620.646,123.343L619.962,122.159L616.785,122.078L616.272,120.03L615.057,120.013L615.246,117.504L612.249,115.68L607.965,115.875L605.031,116.239L602.646,113.984L600.603,113.04L596.724,111.25L596.256,111.034L589.821,112.511L589.92,121.727L588.642,121.85L586.887,119.891L585.195,119.188L582.36,119.709L581.253,120.542L581.118,119.933L581.73,118.892L581.253,118.02L578.355,117.166L577.23,114.923L575.844,114.288L575.763,113.476L578.193,113.713L578.292,111.885L580.416,111.479L582.603,111.851L583.053,109.414L582.603,107.869L580.101,107.988L577.977,107.378L575.088,108.479L572.757,109.003L571.479,108.597L571.74,107.311L570.147,105.639L568.284,105.711L566.169,104.014L567.609,102.119L566.88,101.611L568.878,98.865L571.443,100.312L571.758,98.488L576.915,95.767L580.821,95.704L586.329,97.435L589.29,98.446L591.945,97.392L595.905,97.342L599.109,98.636L599.829,97.896L603.348,98.002L603.969,96.817L599.919,95.099L602.322,93.88L601.854,93.199L604.248,92.552L602.448,90.838L603.591,89.983L612.942,89.116L614.166,88.498L620.421,87.575L622.671,86.539L627.162,87.076L627.954,89.666L630.564,89.056L633.768,89.911L633.561,91.274L635.964,91.134L642.228,88.773L641.31,89.556L644.505,91.49L650.086,97.837L651.418,96.529L654.865,97.968L658.456,97.329L659.842,97.777L661.039,99.22L662.785,99.707L663.856,100.769L667.078,100.435ZM589.92,121.727L589.821,112.511L596.256,111.034L596.724,111.25L600.603,113.04L602.646,113.984L605.031,116.239L607.965,115.875L612.249,115.68L615.246,117.504L615.057,120.013L616.272,120.03L616.785,122.078L619.962,122.159L620.646,123.343L621.582,123.327L622.671,121.541L625.974,119.798L627.405,119.336L628.152,119.582L626.046,121.198L627.891,122.142L629.673,121.52L632.634,122.836L629.439,124.634L627.531,124.389L626.505,124.452L626.145,123.758L626.667,122.599L623.328,123.178L622.527,124.786L621.339,126.166L619.251,126.047L618.603,127.152L620.439,127.744L620.979,129.606L619.575,132.136L617.685,131.612L616.299,131.595L616.362,130.063L613.041,128.992L610.422,127.77L608.793,126.593L605.94,124.867L604.707,122.29L603.87,121.833L601.161,121.947L600.207,121.435L599.937,119.442L596.571,118.122L594.465,119.573L592.332,120.437L592.737,121.693ZM802.502,231.502L806.84,233.224L811.457,234.655L813.185,235.932L814.571,237.189L814.958,238.666L819.116,240.21L819.728,241.535L817.424,241.806L817.982,243.469L820.214,245.11L821.834,247.763L823.265,247.679L823.166,248.787L825.101,249.211L824.345,249.68L827,250.734L826.73,251.457L825.074,251.631L824.453,250.984L822.311,250.704L819.782,250.328L817.838,248.732L816.416,247.357L815.12,245.17L811.862,244.074L809.747,244.789L808.217,245.614L808.532,247.459L806.57,248.318L805.175,247.899L802.583,247.793L802.547,239.648ZM831.599,234.151L832.553,234.951L832.85,236.25L832.067,236.914L831.599,235.442L831.014,234.473L829.88,233.656L828.458,232.59L826.658,231.853L827.351,231.248L828.701,231.951L829.547,232.501L830.6,233.102ZM828.251,239.601L826.883,240.21L825.605,240.794L824.273,240.79L822.221,240.067L820.799,239.368L821.006,238.594L823.247,238.958L824.615,238.763L824.993,237.566L825.353,237.502L825.596,238.831L827.018,238.641L827.72,237.786L829.115,236.893L828.845,235.42L830.339,235.374L830.843,235.784L830.798,237.168L829.961,238.696L828.647,238.899ZM836.9,238.349L837.656,238.916L838.871,240.502L840.05,241.349L839.699,242.051L838.997,242.301L837.917,241.34L836.819,239.753L836.288,237.849L836.63,237.608ZM802.502,231.502L802.547,239.648L802.583,247.793L800.36,245.741L797.822,245.242L797.201,245.952L794.033,246.029L795.095,243.993L796.67,243.299L796.022,240.583L794.816,238.484L789.974,236.368L787.913,236.157L784.16,233.846L783.422,235.061L782.459,235.281L781.892,234.367L781.883,233.279L779.975,232.052L782.666,231.151L784.448,231.198L784.241,230.537L780.578,230.533L779.588,229.044L777.356,228.583L776.303,227.343L779.669,226.738L780.947,225.925L784.961,226.949L785.357,227.88L786.059,231.921L788.642,233.419L790.73,230.766L793.601,229.26L795.824,229.255L797.966,230.127L799.82,231.024ZM762.425,247.23L762.677,247.725L762.722,248.483L761.093,250.349L758.951,250.899L758.654,250.599L758.879,249.748L759.95,248.225ZM785.528,242.237L785.285,240.354L785.726,239.457L786.248,238.611L786.815,239.343L786.815,240.536ZM744.703,214.657L743.281,216.912L745.117,219.282L744.685,220.433L747.493,222.743L744.532,223.039L743.695,224.745L743.803,227.008L741.4,228.718L741.337,231.21L740.374,235.031L740.005,234.143L737.161,235.268L736.171,233.741L734.389,233.597L733.138,232.797L730.168,233.694L729.259,232.488L727.621,232.624L725.56,232.336L725.173,228.98L723.931,228.286L722.725,226.149L722.383,223.962L722.671,221.643L724.156,219.984L724.579,221.656L726.289,223.069L727.9,222.557L729.493,222.739L730.951,221.474L732.148,221.254L734.515,221.956L736.549,221.423L737.836,217.945L738.799,217.077L739.663,214.234L742.534,214.234ZM773.432,232.006L776.177,232.734L777.086,234.646L774.98,233.614L772.892,233.406L771.479,233.571L769.751,233.483L770.336,232.107ZM767.186,234.477L765.458,234.02L764.972,232.945L767.501,232.822L768.122,233.648ZM769.832,219.565L770.012,220.928L771.488,221.148L771.722,222.168L771.587,224.355L770.3,224.11L769.922,225.629L770.948,226.949L770.246,227.25L769.238,225.667L768.5,222.472L769.004,220.475ZM757.322,222.811L760.193,222.705L762.668,220.89L763.1,221.448L761.093,223.932L759.212,224.41L756.809,223.924L752.642,224.046L750.455,224.406L750.104,226.298L752.336,228.523L753.686,227.389L758.348,226.539L758.15,227.69L757.061,227.326L755.972,228.794L753.767,229.763L756.134,232.966L755.684,233.825L757.925,236.711L757.907,238.353L756.575,239.085L755.594,238.209L756.8,236.161L754.343,237.13L753.722,236.436L754.046,235.471L752.246,234.007L752.435,231.57L750.761,232.327L750.977,235.243L751.076,238.823L749.491,239.182L748.42,238.45L749.131,236.148L748.744,233.736L747.691,233.719L746.917,232.006L747.952,230.368L748.312,228.384L749.563,224.614L750.086,223.585L752.219,221.728L754.172,222.464ZM750.734,250.645L747.421,248.893L749.752,248.402L751.067,249.164L751.94,249.926L751.787,250.599ZM753.353,246.342L755.018,246.151L757.259,245.237L756.89,246.625L753.137,247.336L749.806,247.027L749.806,246.113L751.787,245.593ZM745.648,245.906L747.196,245.703L747.817,246.765L744.928,247.268L743.191,247.603L741.85,247.582L742.705,246.143L744.082,246.122L744.748,245.237ZM721.213,241.057L721.555,241.945L726.352,242.195L726.901,241.162L731.536,242.364L732.445,243.985L736.198,244.442L739.267,245.927L736.414,246.879L733.66,245.872L731.401,245.94L728.809,245.754L726.469,245.305L723.571,244.353L721.735,244.103L720.691,244.416L716.137,243.388L715.705,242.313L713.41,242.127L715.129,239.741L718.162,239.889L720.178,240.866ZM710.926,227.711L711.349,229.454L712.222,230.851L714.058,231.071L715.273,232.653L714.643,235.763L714.544,239.631L711.772,239.682L709.666,237.591L706.462,235.552L705.391,234.037L703.501,232.002L702.259,230.127L700.351,226.628L698.155,224.542L697.426,222.392L696.499,220.441L694.249,218.867L692.944,216.726L691.063,215.33L688.453,212.571L688.237,211.302L689.839,211.403L693.709,211.885L695.923,214.327L697.858,216.024L699.235,217.065L701.602,219.752L704.149,219.79L706.246,221.503L707.695,223.598L709.594,224.74L708.595,226.78L710.026,227.647ZM278.418,356.591L279.372,357.75L280.623,359.625L283.872,361.127L287.373,361.749L286.248,363.001L283.872,363.124L282.603,362.244L281.091,362.176L278.418,362.172ZM305.94,300.542L305.31,302.543L304.644,305.112L304.671,307.6L304.122,308.158L303.933,309.775L303.762,311.078L306.939,313.219L306.597,314.945L308.154,316.033L308.028,317.256L305.625,320.459L301.917,321.8L296.904,322.321L294.159,322.071L294.69,323.56L294.177,325.431L294.636,326.692L293.133,327.572L290.577,327.919L288.174,327.005L287.202,327.661L287.553,330.145L289.245,330.898L290.613,330.111L291.351,331.41L289.056,332.184L287.049,333.737L286.68,336.255L286.086,337.592L283.728,337.6L281.766,338.878L281.046,340.753L283.503,342.585L285.897,343.088L285.033,345.335L282.081,346.744L280.461,349.672L278.175,350.663L277.158,351.83L277.959,354.429L279.624,355.876L278.571,355.749L276.258,355.355L270.21,355.021L269.175,353.565L269.229,351.691L267.564,351.852L266.682,350.946L266.466,348.297L268.383,347.197L269.175,345.61L268.878,344.345L270.21,342.212L271.119,338.904L270.849,337.435L271.947,336.961L271.677,336.018L270.516,335.518L271.344,334.469L270.21,333.521L269.625,330.635L270.633,330.128L270.21,327.081L270.795,324.521L271.47,322.291L272.964,321.381L272.208,318.944L272.199,316.646L274.089,315.013L274.026,312.923L275.457,310.485L275.466,308.184L274.818,307.727L273.666,303.411L275.205,300.842L274.962,298.422L275.862,296.149L277.5,293.801L279.264,292.248L278.517,291.266L279.039,290.462L278.958,286.295L281.676,285.063L282.54,282.465L282.234,281.839L284.313,279.579L287.589,280.189L289.056,281.995L290.037,279.986L292.881,280.087L293.286,280.624L297.885,284.704L299.928,285.08L302.979,286.929L305.553,287.907L305.913,289.011L303.456,292.811L305.976,293.488L308.784,293.873L310.764,293.471L313.032,291.554L313.437,289.35L314.679,288.867L315.93,290.31L315.876,292.307L313.77,293.687L312.096,294.707L309.27,297.131ZM278.418,356.591L278.418,362.172L281.091,362.176L282.603,362.244L281.775,363.255L279.633,364.03L278.4,363.949L276.924,363.746L275.106,362.997L272.487,362.633L269.337,361.237L266.79,359.895L263.343,357.094L265.404,357.619L268.914,359.29L272.235,360.187L273.522,359.041L274.332,357.327L276.636,356.295ZM276.024,268.95L277.248,270.651L277.581,272.454L278.895,273.512L278.103,275.932L279.453,278.737L280.434,282.182L282.234,281.839L282.54,282.465L281.676,285.063L278.958,286.295L279.039,290.462L278.517,291.266L279.264,292.248L277.5,293.801L275.862,296.149L274.962,298.422L275.205,300.842L273.666,303.411L274.818,307.727L275.466,308.184L275.457,310.485L274.026,312.923L274.089,315.013L272.199,316.646L272.208,318.944L272.964,321.381L271.47,322.291L270.795,324.521L270.21,327.081L270.633,330.128L269.625,330.635L270.21,333.521L271.344,334.469L270.516,335.518L271.677,336.018L271.947,336.961L270.849,337.435L271.119,338.904L270.21,342.212L268.878,344.345L269.175,345.61L268.383,347.197L266.466,348.297L266.682,350.946L267.564,351.852L269.229,351.691L269.175,353.565L270.21,355.021L276.258,355.355L278.571,355.749L276.348,355.732L275.142,356.345L272.892,357.247L272.487,359.582L271.425,359.642L268.608,358.829L265.746,357.086L262.632,355.656L261.849,354.073L262.56,352.609L261.3,350.946L260.976,346.685L262.047,344.282L264.684,342.348L260.886,341.62L263.271,339.411L264.117,335.256L266.898,336.136L268.203,330.957L266.529,330.293L265.746,333.415L264.171,333.064L264.954,329.489L265.809,324.855L266.952,323.146L266.232,320.709L266.034,317.89L267.087,317.81L268.617,313.773L270.345,309.775L271.407,306.047L270.831,302.302L271.578,300.241L271.272,297.152L272.739,294.101L273.189,289.265L273.99,284.073L274.773,278.483L274.593,274.392L274.071,270.871L275.358,270.232ZM523.346,236.25L523.796,238.552L523.553,239.851L524.048,241.302L525.497,242.698L526.847,245.851L525.866,245.597L522.509,246.016L521.834,246.316L521.123,247.912L521.681,249.016L521.24,251.974L520.934,254.483L521.609,254.927L523.355,255.9L524.039,255.448L524.246,258.143L522.338,258.122L521.312,256.747L520.385,255.68L518.468,255.333L517.91,254.022L516.38,254.813L514.382,254.462L513.545,253.328L511.961,253.095L510.782,253.159L510.647,252.38L509.783,252.316L508.64,252.168L507.092,252.545L506.003,252.481L505.391,252.71L505.526,249.735L504.689,248.809L504.5,247.273L504.869,245.766L504.365,244.801L504.32,243.227L501.287,243.249L501.503,242.347L500.225,242.356L500.09,242.792L498.542,242.889L497.921,244.345L497.543,244.971L496.157,244.62L495.338,244.971L493.682,245.17L492.728,243.862L492.152,243.054L491.432,241.556L490.82,239.694L483.44,239.66L482.558,239.961L481.838,239.914L480.803,240.249L480.452,239.474L481.091,239.212L481.172,238.12L481.577,237.477L482.486,236.952L483.143,237.206L483.998,236.25L485.366,236.275L485.519,236.982L486.455,237.426L487.931,235.861L489.38,234.638L490.019,233.838L489.929,231.781L491.018,229.353L492.161,228.066L493.808,226.86L494.096,226.061L494.159,225.147L494.564,224.279L494.438,222.862L494.744,220.644L495.239,219.087L495.986,217.75L496.13,216.24L496.355,214.496L497.327,213.227L498.668,212.423L500.729,213.269L502.322,214.192L504.149,214.441L506.012,214.928L506.759,213.417L507.101,213.223L508.244,213.476L511.025,212.228L512.015,212.757L512.825,212.681L513.194,212.076L514.13,211.86L516.011,212.122L517.613,212.182L518.432,211.915L519.953,213.98L521.069,214.28L521.744,213.862L522.896,214.027L524.291,213.498L524.885,214.564L527.081,216.227L526.937,219.151L527.936,219.489L527.135,220.378L526.172,221.042L525.218,222.345L524.687,223.505L524.552,225.515L523.967,226.467L523.949,228.354L523.229,229.052L523.139,230.537L522.797,230.732L522.563,232.099L523.193,233.233ZM553.965,229.209L552.48,227.144L552.453,218.038L554.64,215.203L555.324,214.416L556.926,214.369L559.149,212.605L562.407,212.495L569.472,204.993L571.218,202.906L572.343,201.37L572.343,200.067L572.343,197.545L572.352,196.513L572.37,196.475L573.171,196.424L574.323,196.052L575.646,195.802L576.834,194.947L577.779,194.939L577.833,195.628L577.608,197.084L577.617,198.396L577.086,199.301L576.384,202.005L575.178,204.794L573.63,207.988L571.488,211.653L569.355,214.45L566.412,217.86L563.91,219.887L560.175,222.367L557.844,224.271L555.108,227.296L554.532,228.616ZM548.006,236.69L544.415,234.193L544.244,232.742L535.181,227.652L534.758,227.377L534.731,224.724L535.451,223.712L536.684,222.058L537.593,220.234L536.486,217.365L536.198,216.113L535.01,214.374L536.549,212.884L538.241,211.234L539.546,211.653L539.546,213.058L540.401,213.878L542.138,213.878L545.306,216.003L546.089,216.028L546.674,215.96L547.232,216.248L548.897,216.447L549.635,215.402L551.922,214.357L552.93,215.203L554.64,215.203L552.453,218.038L552.48,227.144L553.965,229.209L552.21,230.207L551.598,231.248L550.662,231.435L550.302,233.195L549.5,234.202L549.014,235.865ZM511.421,204.426L509.513,203.334L508.649,202.614L508.487,201.836L508.892,200.795L508.883,199.775L507.443,198.214L507.164,197.143L507.191,196.538L506.273,195.802L506.246,194.351L505.724,193.386L504.842,193.53L505.094,192.611L505.742,191.571L505.454,190.534L506.282,189.768L505.76,189.184L506.417,187.64L507.56,185.799L509.72,185.972L509.594,176.05L509.621,175L512.501,174.992L512.501,169.999L522.554,169.999L532.247,169.999L542.165,169.999L542.975,172.453L542.426,172.906L542.786,175.479L543.704,178.466L544.658,179.079L546.026,180.006L544.757,181.432L542.921,181.843L542.129,182.608L541.886,184.271L540.806,187.944L541.076,188.943L540.671,191.092L539.663,193.555L538.151,194.795L537.08,196.703L536.828,197.723L535.64,198.425L534.902,201.04L534.938,203.287L534.911,201.341L534.56,201.29L534.605,200.046L534.308,199.187L533.021,198.201L532.715,196.399L533.021,194.554L531.86,194.38L531.689,194.939L530.186,195.066L530.789,195.798L530.996,197.3L529.628,198.671L528.386,200.473L527.09,200.732L524.993,199.272L524.048,199.788L523.787,200.516L522.5,200.99L522.419,201.506L519.926,201.506L519.584,200.99L517.784,200.905L516.884,201.332L516.191,201.117L514.904,199.661L514.472,198.971L512.672,199.314L511.988,200.473L511.34,202.708L510.485,203.177L509.72,203.452ZM509.594,176.05L509.72,185.972L507.56,185.799L506.417,187.64L505.76,189.184L506.282,189.768L505.454,190.534L505.742,191.571L505.094,192.611L504.842,193.53L505.724,193.386L506.246,194.351L506.273,195.802L507.191,196.538L507.164,197.143L505.58,197.571L504.311,198.582L502.502,201.311L500.153,202.466L497.732,202.314L497.03,202.543L497.282,203.423L495.977,204.299L494.915,205.272L491.765,206.228L491.144,205.661L490.73,205.615L490.262,206.258L488.201,206.444L488.588,205.767L487.805,204.045L487.454,203.008L486.365,202.585L484.889,201.125L485.429,199.944L486.572,200.198L487.274,200.021L488.669,200.046L487.31,197.774L487.4,196.111L487.238,194.452L486.239,192.853L486.491,191.672L484.889,191.617L484.889,190.009L483.854,189.082L484.934,185.79L488.12,183.434L488.255,180.18L489.218,175.106L489.758,174.031L488.714,173.172L488.678,172.377L487.742,171.73L487.13,167.841L489.65,166.474L499.622,171.264ZM270.723,175.715L270.939,177.074L270.75,178.039L270.138,178.457L270.777,179.206L270.732,179.888L269.067,179.465L267.888,179.638L266.367,179.456L265.197,179.921L263.856,179.143L264.072,178.339L266.376,178.686L268.266,178.885L269.166,178.33L268.023,177.247L268.041,176.291L266.466,175.902L267.024,175.212L268.554,175.322ZM270.732,179.888L270.777,179.206L270.138,178.457L270.75,178.039L270.939,177.074L270.723,175.715L271.029,175.288L272.982,175.301L274.467,175.944L275.124,175.881L275.574,176.765L276.942,176.718L276.861,177.463L277.977,177.552L279.201,178.47L278.274,179.486L277.086,178.944L275.943,179.05L275.115,178.931L274.665,179.384L273.711,179.541L273.324,178.931L272.496,179.291L271.497,181.005L270.858,180.607ZM684.448,22.437L689.848,21.875L694.708,23.131L700.468,25.552L699.847,27.799L694.393,28.107L687.436,27.388L683.278,26.432L681.361,24.642L677.95,24.147ZM707.092,26.796L713.428,28.217L712.69,29.233L698.596,30.198L703.159,26.914L705.22,26.635ZM797.075,34.658L803.681,34.768L812.717,36.092L810.746,37.95L801.539,37.882L797.39,38.47L792.44,36.845L793.781,35.127ZM820.556,36.634L826.829,37.29L823.94,38.28L819.944,38.055L815.3,37.07L815.894,36.257ZM799.658,41.576L802.025,40.586L805.157,40.357L808.703,41.314L809.009,41.97L805.22,41.986L800.099,41.707ZM562.119,23.525L566.997,23.072L570.795,23.038L571.308,23.715L572.739,23.114L575.097,22.704L578.805,23.25L577.842,23.631L574.485,23.961L572.235,24.151L571.884,24.562L568.968,24.976L566.259,24.384L567.681,23.601ZM506.831,89.179L502.232,89.217L499.154,88.934L499.721,87.834L503.168,87.025L505.787,87.461L506.894,87.859L506.624,88.544ZM583.773,40.624L589.758,38.432L589.083,37.298L594.672,35.978L602.925,34.37L611.25,33.904L615.525,32.974L620.394,32.652L622.131,33.638L620.448,34.416L611.592,35.656L603.96,36.85L596.193,39.228L592.467,41.669L588.552,44.073L589.056,46.15L593.835,48.198L592.359,48.418L584.196,48.092L583.53,46.984L579.003,46.315L578.643,44.961L581.199,44.428L581.109,43.061L586.068,40.933ZM807.29,90.741L808.154,93.148L808.091,95.607L809.117,98.133L811.637,102.559L807.938,101.734L806.399,105.347L808.838,107.907L808.766,109.655L806.867,108.149L805.229,110.082L804.77,107.984L805.049,105.55L804.761,102.851L805.337,100.964L805.454,97.621L803.987,95.162L804.203,91.743L806.516,90.597L805.526,89.437L806.633,89.086ZM0,52.59L0,52.59L6.129,54.499L12.681,56.987L12.465,58.54L14.148,59.162L13.572,57.346L20.358,57.719L25.254,60.059L22.77,61.146L18.675,61.404L18.612,63.85L17.613,64.366L15.273,64.294L13.365,63.423L10.044,62.695L9.486,61.607L6.939,61.201L4.104,61.523L2.745,60.647L3.285,59.72L0.288,60.313L1.422,61.489L0,62.551L0,62.551L0,52.59ZM900,62.551L899.982,62.564L896.769,63.664L893.529,63.478L895.779,64.811L897.273,66.871L898.425,67.544L898.713,68.577L898.074,69.241L893.412,68.695L886.419,70.578L884.196,70.87L880.371,72.626L876.744,74.158L875.826,75.296L872.253,73.565L865.737,75.529L864.603,74.602L862.191,75.673L858.852,75.33L858.042,76.972L855.045,79.392L855.135,80.403L857.979,80.962L857.646,84.601L855.324,84.694L854.253,86.784L855.297,87.863L850.923,89.141L850.059,91.993L846.323,92.602L845.576,95.141L841.976,97.473L841.049,95.751L839.978,92.103L838.583,86.547L839.789,83.082L841.895,81.588L842.021,80.42L845.909,79.862L850.374,76.713L854.685,74.141L859.176,72.148L861.183,68.623L858.15,68.835L856.647,70.895L850.302,73.642L848.258,70.565L841.805,71.416L835.541,75.605L837.611,77.137L832.031,77.788L828.161,78.046L828.341,76.24L824.462,75.859L821.366,77.09L813.716,76.658L805.49,77.399L797.399,82.278L787.814,88.176L791.756,88.489L792.98,90.055L795.41,90.614L797.012,89.365L799.757,89.526L803.366,92.277L803.447,94.405L801.494,96.901L801.287,99.885L800.153,103.883L796.391,107.501L795.545,109.232L792.152,112.143L788.786,115.029L787.175,116.506L783.845,117.97L782.27,118.003L780.695,116.789L777.338,118.617L776.951,119.451L776.951,119.451L776.6,119.011L776.582,117.741L777.86,117.673L778.22,114.72L777.563,112.579L779.705,111.699L782.747,112.139L784.421,109.706L785.285,106.968L786.248,106.054L787.562,103.803L783.431,104.543L781.271,105.529L777.464,105.525L776.456,103.177L773.495,101.399L769.148,100.6L768.221,98.15L767.348,96.614L766.412,95.539L764.864,93.017L762.668,92.099L758.933,91.354L755.612,91.422L752.507,91.87L750.446,93.114L751.814,93.711L751.85,95.09L750.455,95.89L748.195,98.543L748.222,99.643L744.694,101.222L741.697,100.278L738.718,100.485L737.404,99.648L735.91,99.381L732.247,101.141L728.953,101.556L726.658,102.174L723.508,101.768L721.186,101.793L719.674,100.515L717.226,99.313L714.715,98.983L711.556,99.313L709.189,99.775L705.643,98.725L705.166,96.851L702.223,96.208L699.955,95.916L697.156,94.883L694.564,97.473L695.581,98.945L693.151,100.684L689.533,100.058L687.04,99.965L685.366,98.797L682.765,98.763L680.587,97.993L676.78,99.17L672.01,101.323L669.382,101.755L668.401,101.962L667.078,100.435L663.856,100.769L662.785,99.707L661.039,99.22L659.842,97.777L658.456,97.329L654.865,97.968L651.418,96.529L650.086,97.837L644.505,91.49L641.31,89.556L642.228,88.773L635.964,91.134L633.561,91.274L633.768,89.911L630.564,89.056L627.954,89.666L627.162,87.076L622.671,86.539L620.421,87.575L614.166,88.498L612.942,89.116L603.591,89.983L602.448,90.838L604.248,92.552L601.854,93.199L602.322,93.88L599.919,95.099L603.969,96.817L603.348,98.002L599.829,97.896L599.109,98.636L595.905,97.342L591.945,97.392L589.29,98.446L586.329,97.435L580.821,95.704L576.915,95.767L571.758,98.488L571.443,100.312L568.878,98.865L566.88,101.611L567.609,102.119L566.169,104.014L568.284,105.711L570.147,105.639L571.74,107.311L571.479,108.597L572.757,109.003L571.614,110.484L569.193,110.895L566.709,113.476L568.977,115.85L568.734,117.534L571.461,120.479L569.967,121.486L569.535,122.121L568.437,121.951L566.718,120.432L566.016,120.348L564.441,119.768L563.676,118.744L561.345,118.219L559.824,118.613L559.392,118.147L555.99,116.95L552.309,116.544L550.194,116.116L549.887,116.412L546.701,114.301L543.848,113.357L541.688,111.889L543.506,111.487L545.585,109.397L544.181,108.407L547.871,107.387L547.799,106.841L545.558,107.243L545.639,106.134L546.926,105.436L549.347,105.254L549.743,104.421L549.185,103.041L550.203,101.73L550.176,100.997L546.485,100.185L545.027,100.21L543.479,99.038L541.562,99.436L538.394,98.556L538.448,98.065L537.557,96.982L535.559,96.859L535.352,96.085L535.982,95.577L534.38,94.164L531.788,94.405L531.032,94.278L530.402,94.845L529.466,94.748L528.854,93.144L528.26,92.315L528.746,92.082L530.762,92.167L531.734,91.621L531.014,90.956L529.331,90.516L529.475,90.064L528.458,89.607L526.892,87.969L527.432,87.296L527.189,86.124L524.741,85.527L523.427,85.824L523.076,85.206L520.439,84.575L519.638,83.103L519.422,81.888L518.216,81.313L519.296,80.522L518.549,78.19L520.331,76.747L519.953,76.312L522.797,74.928L520.178,73.743L525.524,70.548L527.846,69.105L528.791,67.832L525.092,66.118L526.109,64.489L523.859,62.627L525.542,60.486L522.635,57.638L524.939,55.755L521.114,54.088L521.483,52.336L523.499,52.108L527.756,51.105L530.33,50.233L534.434,51.748L541.283,52.341L550.734,55.167L552.651,56.356L552.813,58.019L550.041,59.335L545.954,59.999L534.794,58.1L532.958,58.417L537.035,60.249L537.197,61.409L537.359,63.964L540.581,64.726L542.534,65.373L542.858,64.163L541.346,63.088L542.939,62.141L548.987,63.698L551.085,63.088L549.41,61.256L555.234,58.81L557.538,58.954L559.878,59.826L561.327,58.108L559.248,56.619L560.472,55.125L558.636,53.572L565.629,54.376L567.051,55.777L563.892,56.085L563.901,57.473L565.872,58.332L569.733,57.791L570.345,56.195L575.565,55.002L584.295,52.857L586.176,52.98L583.719,54.499L586.815,54.757L588.606,53.902L593.295,53.834L597.003,52.798L599.856,54.304L602.691,52.65L600.072,51.198L601.377,50.373L608.757,51.13L612.222,51.913L621.276,54.769L622.95,53.462L620.412,52.138L620.34,51.609L617.325,51.363L618.153,50.178L616.812,48.228L616.74,47.428L621.348,45.164L622.995,42.892L624.849,42.401L631.473,43.061L631.986,44.449L629.619,46.476L631.176,47.276L631.977,49.023L631.41,52.446L634.173,53.978L633.093,55.65L628.197,59.2L631.059,59.568L632.049,58.667L634.803,58.028L635.469,56.788L637.629,55.599L636.171,54.177L637.341,52.527L634.605,52.319L634.002,50.932L636,48.422L632.751,46.383L637.224,44.699L636.648,42.917L637.899,42.862L639.204,44.25L638.223,46.662L640.896,47.119L639.753,45.317L643.938,44.331L649.131,44.199L653.749,45.625L651.526,43.544L651.274,40.878L655.621,40.374L661.642,40.484L667.06,40.158L665.026,38.851L667.915,37.209L670.786,37.141L675.646,35.902L682.252,35.567L683.089,34.882L689.65,34.649L691.693,35.212L697.309,33.883L701.899,33.926L702.592,32.847L704.977,31.78L710.881,30.756L715.165,31.564L711.763,32.182L717.424,32.563L718.099,33.799L720.385,33.194L727.693,33.223L733.327,34.446L735.334,35.381L734.713,36.68L731.95,37.421L725.38,38.809L723.499,39.549L726.604,39.9L730.294,40.531L732.553,40.057L733.822,41.661L734.92,41.013L738.916,40.62L746.944,41.03L747.547,42.198L758.006,42.57L758.141,40.662L763.451,41.102L767.438,41.085L771.479,42.405L772.631,44.005L771.146,45.05L774.287,47.018L778.22,48.033L780.632,45.41L784.646,46.535L788.903,45.862L793.745,46.633L795.581,45.93L799.676,46.281L797.867,43.958L801.17,42.875L823.751,44.5L825.875,45.985L832.418,47.893L842.516,47.42L847.493,47.834L849.572,48.867L849.275,50.695L852.354,51.406L855.702,50.894L860.13,50.83L864.855,51.321L869.589,51.042L873.945,53.267L877.041,52.468L875.025,50.868L876.132,49.76L884.106,50.458L889.308,50.305L896.499,51.499L900,52.59L900,62.551ZM900,47.919L897.255,48.046L896.814,47.255L900,46.21L900,47.919ZM0,46.21L0,46.209L0,46.209L0.324,46.108L2.439,46.112L6.057,46.827L5.841,47.17L3.267,47.767L0,47.919L0,47.919L0,46.21ZM533.588,110.07L534.245,109.452L536.027,109.989L536.828,110.087L537.152,110.582L537.53,110.658L537.548,110.874L538.772,111.474L541.328,111.326L540.833,112.215L538.097,112.651L534.704,114.098L533.318,113.586L533.867,112.414L531.131,111.682L531.581,111.204L533.966,110.37ZM252.552,158.024L253.722,157.825L255.378,157.901L255.45,158.549L252.723,158.951ZM255.522,157.402L257.502,158.523L257.07,160.301L256.611,159.983L256.647,158.676L255.531,157.686ZM254.523,161.976L255.279,162.073L256.152,164.151L256.161,165.602L255.549,165.725L254.919,164.286L253.983,163.563ZM297.003,354.623L300,353.125L302.124,353.751L303.627,352.749L305.625,353.874L304.878,354.75L301.503,355.499L300.378,354.623L298.254,355.749ZM487.859,25.814L488.804,24.959L492.476,24.875L495.626,25.746L503.861,27.608L497.57,28.594L496.175,30.435L493.988,30.904L492.8,32.978L489.785,33.075L484.403,31.548L486.671,30.659L482.927,29.94L478.058,27.828L476.114,25.869L482.927,24.972L484.295,25.848ZM527.756,51.105L523.499,52.108L521.483,52.336L522.536,50.585L519.332,49.59L515.453,50.437L514.22,52.269L511.835,53.377L509.153,52.772L505.895,52.895L503.114,51.575L501.611,52.235L500.063,52.336L499.694,53.982L494.987,53.58L494.321,54.973L491.918,54.964L490.271,56.746L487.769,59.517L483.89,63.033L484.799,63.888L483.926,64.878L481.451,64.836L479.831,67.18L479.984,70.498L481.577,71.767L480.749,74.704L478.67,76.417L477.572,77.86L475.889,76.324L470.957,79.218L467.618,79.802L464.162,78.529L463.271,75.842L462.479,70.074L464.783,68.462L471.38,66.364L476.321,63.787L480.893,60.3L486.905,55.472L491.09,53.593L497.957,50.458L503.447,49.362L507.56,49.493L511.367,47.424L515.921,47.534L520.412,47.034L528.233,48.867L525.011,49.535ZM518.522,24.858L514.814,26.203L507.56,26.5L500.189,26.085L499.739,25.395L496.157,25.349L493.421,24.202L501.143,23.504L504.77,24.105L507.299,23.356L513.617,23.982ZM511.808,30.367L506.228,31.387L501.818,30.807L503.537,30.164L502.034,29.364L507.209,28.861L508.199,29.8ZM333.093,18.43L341.481,16.937L350.257,17.051L353.443,16.128L362.281,15.887L382.252,16.2L397.885,18.185L393.268,19.145L383.71,19.255L370.246,19.501L371.506,19.945L380.362,19.67L387.886,20.533L392.746,19.767L394.825,20.664L392.08,22.12L398.443,21.189L410.575,20.22L418.072,20.703L419.476,21.773L409.288,23.55L407.875,24.126L399.883,24.557L405.67,24.676L402.754,26.5L400.738,28.12L400.819,30.904L403.816,32.538L399.91,32.639L395.797,33.431L400.414,34.755L400.999,36.879L398.326,37.112L401.566,39.261L396.013,39.439L398.911,40.459L398.092,41.339L394.573,41.724L391.081,41.733L394.213,43.425L394.249,44.538L389.308,43.506L388.021,44.174L391.396,44.8L394.672,46.328L395.617,48.342L391.162,48.824L389.236,47.86L386.14,46.421L386.995,48.118L384.097,49.434L390.685,49.539L394.132,49.675L387.427,51.854L380.632,53.826L373.315,54.689L370.561,54.698L367.969,55.662L364.495,58.303L359.122,60.054L357.394,60.156L354.064,60.77L350.473,61.354L348.33,62.898L348.294,64.654L347.025,66.296L342.948,68.293L343.956,70.248L342.831,72.313L341.553,74.754L338.034,74.907L334.344,72.867L329.34,72.854L326.919,71.483L325.245,69.042L320.916,65.932L319.647,64.303L319.305,62.06L315.849,59.75L316.749,57.909L315.075,57.029L317.55,54.105L321.312,53.174L322.302,52.129L322.824,50.178L319.962,51.063L318.603,51.435L316.362,51.791L313.293,50.974L313.122,49.277L314.103,47.948L316.425,47.91L321.528,48.575L317.226,46.988L314.985,46.133L312.501,46.484L310.413,45.862L313.203,43.535L311.682,42.604L309.702,40.874L306.687,38.225L303.51,37.251L303.537,36.206L296.832,34.742L291.522,34.56L284.835,34.662L278.742,34.848L275.835,34.053L271.497,32.478L278.058,31.691L283.089,31.56L272.397,30.909L266.754,29.889L267.105,28.92L276.564,27.714L285.726,26.512L286.689,25.607L279.939,24.705L282.126,23.711L290.775,21.963L294.411,21.697L293.376,20.576L299.298,19.915L306.984,19.522L314.661,19.501L317.388,20.279L324.021,18.904L329.988,19.839L333.498,20.034L338.691,20.846L332.751,19.501ZM622.338,346.562L623.949,347.349L626.316,347.663L626.397,348.136L625.704,349.275L621.861,349.435L621.798,348.107L622.167,347.074ZM762.425,247.23L762.713,246.642L764.864,246.079L766.61,245.995L767.393,245.682L768.338,245.995L767.42,246.672L764.819,247.763L762.722,248.483L762.677,247.725ZM490.865,296.441L492.062,295.206L493.043,295.891L493.466,296.958L494.591,297.14L496.166,297.614L497.507,297.432L499.739,296.154L499.739,286.921L500.414,287.293L501.899,289.671L501.665,291.195L502.223,292.07L504.014,291.817L505.265,290.699L506.453,289.95L507.065,288.753L508.28,288.173L509.333,288.474L510.53,289.176L512.564,289.299L514.166,288.715L514.418,287.936L514.85,286.739L516.218,286.54L516.965,285.601L517.802,283.938L520.043,282.067L523.58,280.227L524.597,280.256L525.803,280.68L526.649,280.379L527.981,280.629L529.178,284.149L529.826,285.922L529.385,288.711L529.592,289.608L528.332,289.151L527.612,289.328L527.378,290.056L526.694,290.996L526.712,291.859L528.206,293.213L529.673,292.946L530.177,291.833L532.076,291.855L531.446,293.674L531.158,295.752L530.51,296.882L528.8,298.142L528.314,298.506L527.252,299.776L526.559,301.058L525.137,302.852L522.311,305.429L520.547,306.931L518.657,308.069L516.047,309.038L514.778,309.169L514.454,309.863L512.933,309.491L511.691,309.969L508.982,309.487L507.47,309.792L506.435,309.66L503.861,310.646L501.719,311.044L500.18,311.988L499.037,312.047L497.984,311.158L497.138,311.112L496.058,309.995L495.941,310.342L495.608,309.669L495.626,308.205L494.816,306.529L495.617,306.072L495.554,304.155L493.916,301.815L492.665,299.695L492.656,299.691ZM522.446,297.389L521.357,296.619L520.187,297.127L518.828,298.109L517.496,299.691L519.377,301.612L520.268,301.363L520.727,300.567L522.122,300.174L522.545,299.361L523.31,298.142ZM522.446,297.389L523.31,298.142L522.545,299.361L522.122,300.174L520.727,300.567L520.268,301.363L519.377,301.612L517.496,299.691L518.828,298.109L520.187,297.127L521.357,296.619ZM157.178,143.663L160.022,143.468L163.199,143.197L162.965,143.688L166.736,144.902L172.442,146.663L177.41,146.646L179.399,146.646L179.399,145.613L183.728,145.613L184.646,146.502L185.924,147.289L187.409,148.389L188.237,149.697L188.858,151.072L190.154,151.825L192.224,152.574L193.799,150.598L195.842,150.551L197.606,151.55L198.857,153.259L199.721,154.724L201.197,156.15L201.746,157.901L202.448,159.073L204.401,159.852L206.174,160.402L207.146,160.326L206.183,162.518L205.742,164.32L205.562,167.667L205.319,168.89L205.751,170.253L206.525,171.471L207.029,173.409L208.685,175.271L209.27,176.697L210.251,177.929L212.906,178.593L213.932,179.638L216.128,178.94L218.036,178.686L219.908,178.237L221.483,177.81L223.067,176.79L223.67,175.33L223.868,173.232L224.3,172.5L225.992,171.844L228.638,171.264L230.852,171.353L232.373,171.141L232.967,171.67L232.886,172.876L231.545,174.361L230.951,175.885L231.41,176.321L231.032,177.4L230.411,179.35L229.772,178.707L229.25,178.749L228.773,178.783L227.882,180.294L227.423,179.998L227.126,180.112L227.144,180.48L224.831,180.45L222.5,180.455L222.491,181.864L221.366,181.868L222.293,182.706L223.22,183.281L223.499,183.823L223.904,183.975L223.841,184.826L220.628,184.834L219.431,186.869L219.782,187.339L219.494,187.923L219.431,188.651L216.605,185.96L215.309,185.151L213.275,184.496L211.871,184.678L209.864,185.621L208.604,185.867L206.84,185.207L204.968,184.733L202.628,183.586L200.756,183.235L197.93,182.071L195.833,180.878L195.203,180.209L193.808,180.061L191.252,179.27L190.208,178.127L187.517,176.71L186.266,175.132L185.672,173.913L186.509,173.672L186.248,172.957L186.824,172.309L186.833,171.446L185.996,170.32L185.771,169.326L184.925,168.065L182.729,165.581L180.209,163.626L178.994,162.069L176.852,161.049L176.393,160.436L176.771,158.891L175.493,158.308L174.017,157.093L173.396,155.35L172.055,155.147L170.597,153.831L169.427,152.612L169.319,151.833L167.978,149.946L167.087,148.034L167.132,147.073L165.323,146.083L164.486,146.189L163.055,145.499L162.659,146.515L163.073,147.716L163.316,149.595L164.171,150.623L166.025,152.345L166.439,152.934L166.817,153.111L167.15,153.97L167.591,153.936L168.095,155.549L168.86,156.183L169.391,157.072L170.957,158.341L171.785,160.669L172.532,161.765L173.225,162.937L173.36,164.253L174.566,164.337L175.574,165.471L176.474,166.588L176.42,167.037L175.367,167.955L174.926,167.942L174.26,166.423L172.631,164.997L170.822,163.787L169.544,163.152L169.625,161.325L169.247,159.97L168.059,159.196L166.34,158.079L166.007,158.401L165.377,157.749L163.838,157.144L162.362,155.693L162.542,155.506L163.577,155.646L164.504,154.711L164.594,153.585L162.668,151.8L161.201,151.11L160.283,149.549L159.356,147.907L158.195,145.91ZM305.94,300.542L307.56,300.275L310.071,302.209L310.998,302.133L313.572,303.736L315.534,305.12L316.974,306.821L315.876,308.006L316.569,309.419L315.48,310.993L312.663,312.381L310.818,311.882L309.459,312.148L307.155,311.078L305.454,311.158L303.933,309.775L304.122,308.158L304.671,307.6L304.644,305.112L305.31,302.543ZM316.569,309.419L315.876,308.006L316.974,306.821L315.534,305.12L313.572,303.736L310.998,302.133L310.071,302.209L307.56,300.275L305.94,300.542L309.27,297.131L312.096,294.707L313.77,293.687L315.876,292.307L315.93,290.31L314.679,288.867L313.437,289.35L313.923,287.907L314.265,286.426L314.265,285.051L313.365,284.598L312.429,285.004L311.502,284.894L311.205,283.929L310.971,281.64L310.503,280.891L308.82,280.214L307.794,280.705L305.157,280.227L305.319,276.833L304.581,275.441L305.364,274.925L305.121,273.499L305.814,272.403L306.255,270.435L305.661,268.882L304.302,268.18L304.032,267.194L304.401,265.747L299.604,265.645L298.641,262.734L299.37,262.692L299.343,261.613L298.848,260.885L298.74,259.438L297.291,258.697L295.716,258.723L294.681,257.995L292.989,257.5L292.008,256.569L289.209,256.154L286.491,253.916L286.698,252.24L286.392,251.28L286.653,249.405L283.386,249.828L282.063,250.768L279.876,251.779L279.318,252.536L278.031,252.591L276.177,252.38L274.764,252.812L273.63,252.524L273.792,248.724L271.74,250.197L269.535,250.133L268.59,248.8L266.934,248.656L267.465,247.582L266.07,246.062L265.035,243.811L265.692,243.354L265.692,242.297L267.204,241.573L266.952,240.223L267.591,239.351L267.771,238.188L270.633,236.487L272.676,236.004L273.009,235.628L275.268,235.746L276.393,228.891L276.447,227.808L276.06,226.374L274.953,225.464L274.962,223.645L276.366,223.234L276.87,223.492L276.951,222.536L275.493,222.278L275.457,220.712L280.326,220.767L281.154,219.908L281.847,220.699L282.342,222.176L282.81,221.867L284.187,223.188L286.131,223.027L286.617,222.261L288.471,221.677L289.506,221.266L289.794,220.209L291.576,219.498L291.441,218.973L289.326,218.757L288.975,217.183L289.083,215.508L287.958,214.86L288.426,214.627L290.28,214.949L292.269,215.575L292.989,214.983L294.789,214.594L297.579,213.658L298.497,212.706L298.164,212L299.469,211.89L300.045,212.465L299.721,213.561L300.585,213.942L301.152,215.101L300.459,215.986L300.063,218.11L300.702,219.375L300.882,220.534L302.421,221.707L303.654,221.829L303.924,221.338L304.716,221.233L305.85,220.793L306.66,220.128L308.046,220.34L308.649,220.251L310.008,220.454L310.233,219.946L309.819,219.447L310.071,218.723L311.079,218.948L312.258,218.69L313.689,219.218L314.778,219.735L315.552,219.058L316.11,219.163L316.452,219.866L317.649,219.688L318.612,218.74L319.377,216.895L320.853,214.61L321.708,214.492L322.329,215.876L323.724,220.247L325.065,220.657L325.128,222.384L323.256,224.444L324.03,225.197L328.449,225.587L328.539,228.096L330.438,226.454L333.579,227.351L337.737,228.879L338.952,230.343L338.547,231.726L341.454,230.956L346.314,232.281L350.05,232.183L353.749,234.253L356.944,237.054L358.87,237.773L361.003,237.875L361.912,238.662L362.758,241.844L363.172,243.359L362.182,247.493L360.904,249.122L357.385,252.6L355.792,255.427L353.938,257.597L353.317,257.644L352.615,259.484L352.795,264.169L352.102,268.019L351.832,269.669L351.04,270.655L350.599,273.998L348.06,277.261L347.637,279.842L345.612,280.925L345.027,282.427L342.309,282.419L338.376,283.379L336.621,284.492L333.822,285.224L330.879,287.213L328.764,289.692L328.395,291.558L328.809,292.938L328.35,295.464L327.783,296.687L326.028,298.062L323.256,302.463L321.06,304.443L319.359,305.615L318.216,307.993ZM276.177,252.38L278.031,252.591L279.318,252.536L279.876,251.779L282.063,250.768L283.386,249.828L286.653,249.405L286.392,251.28L286.698,252.24L286.491,253.916L289.209,256.154L292.008,256.569L292.989,257.5L294.681,257.995L295.716,258.723L297.291,258.697L298.74,259.438L298.848,260.885L299.343,261.613L299.37,262.692L298.641,262.734L299.604,265.645L304.401,265.747L304.032,267.194L304.302,268.18L305.661,268.882L306.255,270.435L305.814,272.403L305.121,273.499L305.364,274.925L304.581,275.441L304.545,274.671L302.214,273.393L299.892,273.355L295.536,274.083L294.339,276.283L294.276,277.629L293.286,280.624L292.881,280.087L290.037,279.986L289.056,281.995L287.589,280.189L284.313,279.579L282.234,281.839L280.434,282.182L279.453,278.737L278.103,275.932L278.895,273.512L277.581,272.454L277.248,270.651L276.024,268.95L277.599,266.25L276.528,264.152L277.095,263.31L276.654,262.383L277.626,261.135L277.68,259.006L277.797,257.25L278.337,256.404ZM275.268,235.746L273.009,235.628L272.676,236.004L270.633,236.487L267.771,238.188L267.591,239.351L266.952,240.223L267.204,241.573L265.692,242.297L265.692,243.354L265.035,243.811L266.07,246.062L267.465,247.582L266.934,248.656L268.59,248.8L269.535,250.133L271.74,250.197L273.792,248.724L273.63,252.524L274.764,252.812L276.177,252.38L278.337,256.404L277.797,257.25L277.68,259.006L277.626,261.135L276.654,262.383L277.095,263.31L276.528,264.152L277.599,266.25L276.024,268.95L275.358,270.232L274.071,270.871L271.56,269.432L271.344,268.408L266.385,265.899L261.903,263.166L259.977,261.621L258.942,259.556L259.356,258.837L257.232,255.558L254.766,250.945L252.408,245.965L251.382,244.827L250.599,242.986L248.654,241.353L246.872,240.342L247.682,239.225L246.476,236.842L247.25,235.09L249.239,233.512L249.536,234.553L248.825,235.15L248.897,236.064L249.923,235.865L250.941,236.136L251.985,237.397L253.398,236.368L253.875,234.684L255.405,232.509L258.411,231.523L261.138,228.904L261.912,227.279L261.57,225.379L262.236,225.142L263.892,226.327L264.693,227.508L265.854,228.151L267.321,230.774L269.184,231.088L270.561,230.423L271.47,230.859L272.964,230.643L274.881,231.811L273.27,234.358L274.017,234.418ZM282.81,221.867L282.342,222.176L281.847,220.699L281.154,219.908L280.326,220.767L275.457,220.712L275.493,222.278L276.951,222.536L276.87,223.492L276.366,223.234L274.962,223.645L274.953,225.464L276.06,226.374L276.447,227.808L276.393,228.891L275.268,235.746L274.017,234.418L273.27,234.358L274.881,231.811L272.964,230.643L271.47,230.859L270.561,230.423L269.184,231.088L267.321,230.774L265.854,228.151L264.693,227.508L263.892,226.327L262.236,225.142L261.57,225.379L260.499,224.787L259.266,223.962L258.555,224.36L256.44,224.013L255.828,222.934L255.36,222.976L252.858,221.546L252.525,220.771L253.452,220.585L253.344,219.333L253.929,218.427L255.171,218.258L256.224,216.688L257.178,215.376L256.26,214.78L256.728,213.328L256.17,211.043L256.701,210.388L256.305,208.272L255.297,206.939L255.621,205.725L256.422,205.906L256.89,205.162L256.314,203.689L256.62,203.325L257.907,203.402L259.788,201.658L260.814,201.392L260.841,200.566L261.3,198.451L262.731,197.291L264.306,197.245L264.504,196.724L266.466,196.932L268.428,195.671L269.409,195.112L270.615,193.906L271.497,194.059L272.154,194.719L271.668,195.561L270.066,195.98L269.427,197.228L268.464,197.943L267.735,198.874L267.429,200.66L266.736,202.119L268.032,202.289L268.347,203.435L268.905,203.985L269.094,204.993L268.797,205.919L268.887,206.44L269.508,206.647L270.102,207.523L273.315,207.282L274.764,207.599L276.528,209.749L277.536,209.482L279.336,209.617L280.758,209.33L281.649,209.761L281.199,211.107L280.641,211.949L280.443,213.739L280.947,215.402L281.658,216.142L281.739,216.705L280.479,217.949L281.379,218.499L282.045,219.375ZM256.62,203.325L256.314,203.689L256.89,205.162L256.422,205.906L255.621,205.725L255.297,206.939L254.46,206.22L253.929,204.87L254.541,204.201L253.911,204.032L253.443,203.203L252.201,202.509L251.103,202.669L250.599,203.537L249.59,204.167L249.041,204.252L248.798,204.772L249.986,206.131L249.311,206.452L248.951,206.82L247.781,206.947L247.349,205.454L247.025,205.881L246.197,205.733L245.693,204.726L244.667,204.561L244.019,204.269L242.948,204.273L242.876,204.815L242.588,204.438L242.714,203.943L242.921,203.435L242.831,202.983L243.2,202.686L242.678,202.314L242.669,201.307L243.632,201.083L244.532,201.98L244.478,202.513L245.477,202.623L245.711,202.42L246.404,203.033L247.628,202.856L248.699,202.221L250.212,201.717L251.067,200.973L252.444,201.117L252.354,201.362L253.749,201.451L254.865,201.882L255.675,202.631ZM243.632,201.083L242.669,201.307L242.678,202.314L243.2,202.686L242.831,202.983L242.921,203.435L242.714,203.943L242.588,204.438L241.229,203.884L240.725,203.359L241.013,202.923L240.914,202.373L240.221,201.772L239.24,201.282L238.385,200.96L238.214,200.228L237.557,199.784L237.719,200.511L237.224,201.108L236.648,200.414L235.847,200.169L235.505,199.661L235.523,198.904L235.847,198.112L235.145,197.761L235.721,197.279L236.099,196.957L237.746,197.617L238.313,197.291L239.114,197.503L239.528,198.015L240.266,198.184L240.86,197.651L241.49,199.009L242.462,200.016ZM240.86,197.651L240.266,198.184L239.528,198.015L239.114,197.503L238.313,197.291L237.746,197.617L236.099,196.957L235.721,197.279L234.857,196.492L233.687,195.485L233.138,194.638L232.085,193.855L230.825,192.726L231.104,192.341L231.518,192.713L231.707,192.54L232.481,192.434L232.796,191.862L233.165,191.841L233.111,190.614L233.696,190.555L234.218,190.572L234.758,189.903L235.496,190.411L235.757,190.098L236.216,189.802L237.089,189.112L237.125,188.6L237.368,188.621L237.692,188.025L237.953,187.953L238.376,188.334L238.88,188.448L239.429,188.126L240.059,188.126L240.932,187.8L241.274,187.458L242.129,187.508L241.913,187.75L241.787,188.308L242.048,189.222L241.472,190.077L241.202,191.08L241.121,192.184L241.256,192.827L241.319,193.953L240.932,194.198L240.698,195.269L240.869,195.929L240.365,196.568L240.473,197.241ZM242.129,187.508L241.274,187.458L240.932,187.8L240.059,188.126L239.429,188.126L238.88,188.448L238.376,188.334L237.953,187.953L237.692,188.025L237.368,188.621L237.125,188.6L237.089,189.112L236.216,189.802L235.757,190.098L235.496,190.411L234.758,189.903L234.218,190.572L233.696,190.555L233.111,190.614L233.165,191.841L232.796,191.862L232.481,192.434L231.707,192.54L231.275,191.757L230.519,191.541L230.69,190.538L230.348,190.267L229.835,190.09L228.737,190.386L228.647,190.051L227.891,189.649L227.351,189.15L226.613,188.939L227.135,188.304L226.937,187.813L227.117,187.335L228.296,186.632L229.439,185.68L229.7,185.778L230.249,185.338L230.96,185.304L231.194,185.507L231.581,185.384L232.742,185.608L233.894,185.545L234.704,185.266L234.992,184.986L235.793,185.118L236.387,185.287L237.044,185.228L237.539,185.012L238.682,185.359L239.078,185.414L239.843,185.879L240.563,186.438L241.472,186.823ZM226.613,188.939L227.351,189.15L227.891,189.649L228.647,190.051L228.737,190.386L229.835,190.09L230.348,190.267L230.69,190.538L230.519,191.541L230.24,192.129L228.791,192.091L227.891,191.85L226.856,191.355L225.47,191.198L224.759,190.661L224.84,190.297L225.695,189.666L226.163,189.387L226.028,189.095ZM219.431,188.651L219.494,187.923L219.782,187.339L219.431,186.869L220.628,184.834L223.841,184.826L223.904,183.975L223.499,183.823L223.22,183.281L222.293,182.706L221.366,181.868L222.491,181.864L222.5,180.455L224.831,180.45L227.144,180.48L227.126,182.46L226.928,185.283L227.675,185.283L228.485,185.735L228.701,185.363L229.439,185.68L228.296,186.632L227.117,187.335L226.937,187.813L227.135,188.304L226.613,188.939L226.028,189.095L226.163,189.387L225.695,189.666L224.84,190.297L224.759,190.661L223.481,190.225L221.915,190.178L220.772,189.683ZM227.144,180.48L227.126,180.112L227.423,179.998L227.882,180.294L228.773,178.783L229.25,178.749L229.259,179.118L229.736,179.13L229.691,179.807L229.286,180.89L229.502,181.276L229.241,182.173L229.403,182.41L229.115,183.675L228.62,184.335L228.17,184.415L227.675,185.283L226.928,185.283L227.126,182.46ZM298.164,212L298.497,212.706L297.579,213.658L294.789,214.594L292.989,214.983L292.269,215.575L290.28,214.949L288.426,214.627L287.958,214.86L289.083,215.508L288.975,217.183L289.326,218.757L291.441,218.973L291.576,219.498L289.794,220.209L289.506,221.266L288.471,221.677L286.617,222.261L286.131,223.027L284.187,223.188L282.81,221.867L282.045,219.375L281.379,218.499L280.479,217.949L281.739,216.705L281.658,216.142L280.947,215.402L280.443,213.739L280.641,211.949L281.199,211.107L281.649,209.761L280.758,209.33L279.336,209.617L277.536,209.482L276.528,209.749L274.764,207.599L273.315,207.282L270.102,207.523L269.508,206.647L268.887,206.44L268.797,205.919L269.094,204.993L268.905,203.985L268.347,203.435L268.032,202.289L266.736,202.119L267.429,200.66L267.735,198.874L268.464,197.943L269.427,197.228L270.066,195.98L271.668,195.561L271.596,196.149L270.129,196.441L270.948,197.575L270.921,198.882L269.814,200.338L270.759,202.318L271.839,202.157L272.397,200.351L271.623,199.471L271.497,197.579L274.611,196.559L274.269,195.383L275.142,194.596L276.042,196.352L277.797,196.39L279.417,197.786L279.516,198.612L281.757,198.637L284.43,198.379L285.861,199.496L287.778,199.809L289.173,199.026L289.209,198.396L292.305,198.248L295.302,198.21L293.178,198.95L294.033,200.131L296.031,200.317L297.921,201.548L298.326,203.55L299.622,203.495L300.603,204.083L298.623,205.551L298.407,206.461L299.262,207.392L298.641,207.857L297.102,208.259L297.147,209.414L296.472,210.104ZM308.649,220.251L308.046,220.34L306.66,220.128L305.85,220.793L304.716,221.233L303.924,221.338L303.654,221.829L302.421,221.707L300.882,220.534L300.702,219.375L300.063,218.11L300.459,215.986L301.152,215.101L300.585,213.942L299.721,213.561L300.045,212.465L299.469,211.89L298.164,212L296.472,210.104L297.147,209.414L297.102,208.259L298.641,207.857L299.262,207.392L298.407,206.461L298.623,205.551L300.603,204.083L302.25,205.001L303.789,206.63L303.861,207.916L304.806,207.976L306.147,209.199L307.128,210.066L306.732,212.317L305.211,212.969L305.346,213.557L304.887,214.847L305.994,216.663L306.795,216.667L307.128,218.076ZM313.689,219.218L312.258,218.69L311.079,218.948L310.071,218.723L309.819,219.447L310.233,219.946L310.008,220.454L308.649,220.251L307.128,218.076L306.795,216.667L305.994,216.663L304.887,214.847L305.346,213.557L305.211,212.969L306.732,212.317L307.128,210.066L310.125,210.569L310.395,210.117L312.42,209.935L315.102,210.608L313.806,212.757L314.004,214.467L314.985,215.952L314.544,217.027L314.328,218.169ZM320.853,214.61L319.377,216.895L318.612,218.74L317.649,219.688L316.452,219.866L316.11,219.163L315.552,219.058L314.778,219.735L313.689,219.218L314.328,218.169L314.544,217.027L314.985,215.952L314.004,214.467L313.806,212.757L315.102,210.608L315.957,210.883L317.793,211.475L320.439,213.586ZM465.467,101.34L466.646,101.996L470.246,102.457L468.986,104.167L468.671,105.948L467.978,106.376L466.844,106.147L466.925,106.782L465.098,108.187L465.053,109.316L466.25,108.927L467.105,110.023L467.006,110.73L467.744,111.669L466.871,112.431L467.519,114.364L468.878,114.682L468.59,115.765L466.322,117.178L461.39,116.501L457.754,117.314L457.466,118.816L454.568,119.142L451.751,118.012L450.842,118.549L446.242,117.415L445.243,116.442L446.539,114.944L447.016,109.964L444.433,107.34L442.588,106.075L438.772,105.115L438.52,103.291L441.76,102.745L445.954,103.388L445.162,100.557L447.529,101.632L453.344,99.682L454.1,97.634L456.287,97.13L456.647,98.006L457.808,98.048L458.969,99.051L460.715,100.232L462.002,100.037L464.189,101.175L464.747,101.395ZM471.866,118.431L473.477,117.475L473.9,119.62L473.072,121.549L471.938,121.042L471.362,119.358ZM261.57,225.379L261.912,227.279L261.138,228.904L258.411,231.523L255.405,232.509L253.875,234.684L253.398,236.368L251.985,237.397L250.941,236.136L249.923,235.865L248.897,236.064L248.825,235.15L249.536,234.553L249.239,233.512L250.572,231.642L250.032,230.55L249.077,231.714L247.583,230.618L248.087,229.911L247.664,227.643L248.537,227.267L249.005,225.709L249.95,224.097L249.77,223.078L251.148,222.544L252.858,221.546L255.36,222.976L255.828,222.934L256.44,224.013L258.555,224.36L259.266,223.962L260.499,224.787ZM284.295,178.711L285.573,178.931L286.023,179.431L285.384,180.061L283.503,180.044L282.036,180.133L281.892,179.063L282.252,178.699ZM256.08,178.775L257.763,178.999L259.086,179.6L259.5,180.281L257.745,180.328L256.989,180.747L255.585,180.345L254.154,179.435L254.46,178.864L255.504,178.69ZM244.325,167.028L246.485,167.206L248.456,167.236L250.806,168.086L251.796,169L254.136,168.721L255.018,169.305L257.133,170.854L258.69,171.983L259.518,171.95L261.003,172.457L260.823,173.164L262.668,173.266L264.558,174.29L264.261,174.873L262.596,175.191L260.913,175.314L259.194,175.119L255.612,175.36L257.286,173.968L256.269,173.316L254.658,173.151L253.794,172.428L253.2,171.006L251.787,171.103L249.455,170.43L248.708,169.906L245.45,169.521L244.577,169.034L245.513,168.408L243.056,168.281L241.265,169.58L240.23,169.614L239.87,170.223L238.628,170.498L237.566,170.261L238.88,169.487L239.42,168.586L240.554,168.031L241.832,167.54L243.722,167.303ZM527.981,280.629L526.649,280.379L525.803,280.68L524.597,280.256L523.58,280.227L521.987,279.097L520.052,278.716L519.314,277.129L519.314,276.249L518.243,275.978L515.408,273.232L514.625,271.785L514.121,271.341L513.158,269.339L515.957,269.614L516.767,269.902L517.613,269.847L518.999,268.227L521.168,266.17L522.068,265.975L522.365,265.108L523.796,264.114L525.686,263.771L525.848,264.702L527.936,264.651L529.088,265.18L529.628,265.798L530.816,265.98L532.121,266.784L532.121,269.949L531.635,271.679L531.527,273.55L531.932,274.29L531.653,275.763L531.275,275.987L530.609,277.789ZM523.58,280.227L520.043,282.067L517.802,283.938L516.965,285.601L516.218,286.54L514.85,286.739L514.418,287.936L514.166,288.715L512.564,289.299L510.53,289.176L509.333,288.474L508.28,288.173L507.065,288.753L506.453,289.95L505.265,290.699L504.014,291.817L502.223,292.07L501.665,291.195L501.899,289.671L500.414,287.293L499.739,286.921L499.739,279.622L502.205,279.537L502.277,270.63L504.14,270.55L507.992,269.674L508.946,270.702L510.539,269.724L511.304,269.716L512.708,269.153L513.158,269.339L514.121,271.341L514.625,271.785L515.408,273.232L518.243,275.978L519.314,276.249L519.314,277.129L520.052,278.716L521.987,279.097ZM499.739,286.921L499.739,296.154L497.507,297.432L496.166,297.614L494.591,297.14L493.466,296.958L493.043,295.891L492.062,295.206L490.865,296.441L489.002,294.554L488.03,292.726L487.472,290.293L486.86,288.482L486.023,284.632L485.96,281.64L485.645,280.278L484.673,279.249L483.377,277.18L482.063,274.184L481.523,272.614L479.489,270.173L479.336,268.256L480.542,267.778L482.036,267.355L483.656,267.427L485.15,268.557L485.528,268.383L495.662,268.273L497.39,269.475L503.447,269.826L508.037,268.806L510.089,268.239L511.709,268.383L512.69,268.946L512.708,269.153L511.304,269.716L510.539,269.724L508.946,270.702L507.992,269.674L504.14,270.55L502.277,270.63L502.205,279.537L499.739,279.622ZM408.217,191.012L407.182,189.066L405.94,188.177L407.038,187.703L408.244,185.947L408.838,184.661L409.702,183.861L410.944,184.077L412.159,183.531L413.554,183.505L414.751,184.238L416.407,184.902L417.919,186.743L419.575,188.456L419.692,190.013L420.178,191.444L421.114,192.146L421.33,193.115L421.213,193.894L420.853,194.033L419.494,193.834L419.305,194.114L418.756,194.169L416.956,193.559L415.75,193.534L411.133,193.428L410.458,193.712L409.63,193.631L408.307,194.037L407.893,192.121L410.17,192.176L410.773,191.824L411.223,191.803L412.15,191.228L413.221,191.752L414.31,191.799L415.39,191.236L414.886,190.517L414.058,190.936L413.284,190.923L412.294,190.31L411.502,190.348L410.935,190.94ZM421.213,193.894L421.33,193.115L421.114,192.146L420.178,191.444L419.692,190.013L419.575,188.456L420.412,188.003L420.835,186.531L421.627,186.472L423.373,187.17L424.786,186.675L425.749,186.84L426.127,186.286L436.153,186.247L436.711,184.496L436.279,184.187L435.073,173.397L433.867,162.607L437.692,162.564L446.125,168.019L454.559,173.473L455.153,174.645L456.71,175.36L457.871,175.766L457.898,177.357L460.67,177.112L460.679,182.871L459.311,184.538L459.095,186.078L456.872,186.476L453.461,186.692L452.543,187.58L450.941,187.678L449.338,187.69L448.708,187.208L447.331,187.563L445,188.604L444.523,189.383L442.579,190.504L442.237,191.147L441.193,191.655L439.987,191.321L439.303,191.93L438.934,193.644L436.945,195.717L437.008,196.564L436.324,197.621L436.486,199.073L435.46,199.445L434.875,199.758L434.488,198.688L433.768,198.971L433.336,198.925L432.877,199.652L430.942,199.631L430.249,199.255L429.925,199.483L429.16,198.764L429.295,198.019L428.98,197.727L428.449,197.973L428.548,197.16L429.061,196.517L428.035,195.468L427.738,194.778L427.18,194.228L426.685,194.164L426.082,194.516L425.272,194.85L424.588,195.391L423.517,195.188L422.824,194.554L422.41,194.473L421.753,194.803L421.357,194.808ZM407.344,172.5L407.884,171.666L417.676,171.683L417.199,168.074L417.811,166.787L420.16,166.563L420.079,160.165L428.278,160.296L428.287,156.509L437.692,162.564L433.867,162.607L435.073,173.397L436.279,184.187L436.711,184.496L436.153,186.247L426.127,186.286L425.749,186.84L424.786,186.675L423.373,187.17L421.627,186.472L420.835,186.531L420.412,188.003L419.575,188.456L417.919,186.743L416.407,184.902L414.751,184.238L413.554,183.505L412.159,183.531L410.944,184.077L409.702,183.861L408.838,184.661L408.622,183.315L409.324,182.084L409.63,179.727L409.36,177.26L409.054,176.016L409.306,174.768L408.658,173.579ZM456.728,209.351L454.667,209.643L454.046,207.921L454.163,202.179L453.659,201.662L453.56,200.435L452.696,199.559L451.931,198.823L452.246,197.507L453.11,197.224L453.614,196.132L454.838,195.895L455.387,195.15L456.224,194.418L457.124,194.41L459.032,195.848L458.933,196.682L459.491,198.163L459.005,199.17L459.266,199.843L458.051,201.392L457.277,202.157L456.809,203.732L456.872,205.323ZM487.13,167.841L487.742,171.73L488.678,172.377L488.714,173.172L489.758,174.031L489.218,175.106L488.255,180.18L488.12,183.434L484.934,185.79L483.854,189.082L484.889,190.009L484.889,191.617L486.491,191.672L486.239,192.853L485.537,192.997L485.456,193.792L484.988,193.847L483.296,191.109L482.711,191.008L480.758,192.408L478.823,191.676L477.473,191.532L476.753,191.884L475.286,191.807L473.81,192.874L472.541,192.933L469.508,191.642L468.329,192.256L467.051,192.214L466.115,191.27L463.604,190.335L460.922,190.631L460.274,191.173L459.923,192.611L459.203,193.619L459.032,195.848L457.124,194.41L456.224,194.418L455.387,195.15L455.441,193.437L452.561,192.87L452.48,191.659L451.076,190.026L450.743,188.888L450.941,187.678L452.543,187.58L453.461,186.692L456.872,186.476L459.095,186.078L459.311,184.538L460.679,182.871L460.67,177.112L464.198,175.999L471.434,171.086L480.002,166.322L483.953,167.401L485.357,168.772ZM456.728,209.351L456.872,205.323L456.809,203.732L457.277,202.157L458.051,201.392L459.266,199.843L459.005,199.17L459.491,198.163L458.933,196.682L459.032,195.848L459.203,193.619L459.923,192.611L460.274,191.173L460.922,190.631L463.604,190.335L466.115,191.27L467.051,192.214L468.329,192.256L469.508,191.642L472.541,192.933L473.81,192.874L475.286,191.807L476.753,191.884L477.473,191.532L478.823,191.676L480.758,192.408L482.711,191.008L483.296,191.109L484.988,193.847L485.456,193.792L486.446,194.786L486.167,195.239L486.041,196.069L483.935,198.002L483.269,199.597L482.918,200.897L482.387,201.455L481.883,203.207L480.551,204.235L480.164,205.5L479.597,206.507L479.363,207.548L477.644,208.39L476.24,207.362L475.295,207.404L473.81,208.864L473.081,208.89L471.893,211.302L471.254,213.07L468.653,213.972L467.708,213.84L466.745,214.399L464.747,214.344L463.406,212.778L462.587,210.971L460.814,209.325L458.933,209.355ZM486.239,192.853L487.238,194.452L487.4,196.111L487.31,197.774L488.669,200.046L487.274,200.021L486.572,200.198L485.429,199.944L484.889,201.125L486.365,202.585L487.454,203.008L487.805,204.045L488.588,205.767L488.201,206.444L486.941,208.978L486.338,209.431L486.149,211.369L486.401,212.423L486.194,213.168L487.382,214.475L487.589,215.372L488.516,216.663L489.659,217.467L489.767,218.605L490.028,219.333L489.848,220.683L487.868,220.09L485.843,219.43L482.693,219.333L482.378,219.197L480.902,219.519L479.381,219.185L478.193,219.345L474.125,219.29L474.485,217.319L473.513,215.664L472.37,215.241L471.866,214.12L471.218,213.76L471.254,213.07L471.893,211.302L473.081,208.89L473.81,208.864L475.295,207.404L476.24,207.362L477.644,208.39L479.363,207.548L479.597,206.507L480.164,205.5L480.551,204.235L481.883,203.207L482.387,201.455L482.918,200.897L483.269,199.597L483.935,198.002L486.041,196.069L486.167,195.239L486.446,194.786L485.456,193.792L485.537,192.997ZM452.246,197.507L451.931,198.823L452.696,199.559L453.56,200.435L453.659,201.662L454.163,202.179L454.046,207.921L454.667,209.643L452.651,210.176L452.093,209.3L451.427,207.713L451.229,206.469L451.778,204.218L451.157,203.308L450.914,201.337L450.923,199.521L449.878,198.231L450.059,197.452ZM450.059,197.452L449.878,198.231L450.923,199.521L450.914,201.337L451.157,203.308L451.778,204.218L451.229,206.469L451.427,207.713L452.093,209.3L452.651,210.176L448.726,211.64L447.34,212.499L445.09,213.223L442.858,212.512L442.975,211.526L441.886,209.372L442.543,206.55L443.596,204.451L442.93,200.892L442.588,199.014L442.651,197.592L446.989,197.478L448.096,197.66L448.906,197.253ZM429.925,199.483L430.249,199.255L430.942,199.631L432.877,199.652L433.336,198.925L433.768,198.971L434.488,198.688L434.875,199.758L435.46,199.445L436.486,199.073L437.611,199.619L438.052,200.444L439.177,200.973L440.05,200.342L441.22,200.249L442.93,200.892L443.596,204.451L442.543,206.55L441.886,209.372L442.975,211.526L442.858,212.512L441.724,212.541L439.978,212.05L438.376,212.08L435.415,212.516L433.678,213.235L431.203,214.153L430.717,214.09L430.915,212.029L431.149,211.716L431.077,210.73L430.015,209.685L429.223,209.516L428.494,208.83L429.034,207.722L428.782,206.512L428.899,205.784L429.295,205.784L429.448,204.692L429.25,204.21L429.493,203.863L430.42,203.562L429.799,201.561L429.223,200.524L429.43,199.678ZM415.75,193.534L416.956,193.559L418.756,194.169L419.305,194.114L419.494,193.834L420.853,194.033L421.213,193.894L421.357,194.808L421.753,194.803L422.41,194.473L422.824,194.554L423.517,195.188L424.588,195.391L425.272,194.85L426.082,194.516L426.685,194.164L427.18,194.228L427.738,194.778L428.035,195.468L429.061,196.517L428.548,197.16L428.449,197.973L428.98,197.727L429.295,198.019L429.16,198.764L429.925,199.483L429.43,199.678L429.223,200.524L429.799,201.561L430.42,203.562L429.493,203.863L429.25,204.21L429.448,204.692L429.295,205.784L428.899,205.784L428.197,205.72L427.684,206.727L426.982,206.715L426.487,206.182L426.658,205.179L425.614,203.647L424.957,203.93L424.426,203.985L423.733,204.129L423.76,203.211L423.364,202.555L423.445,201.832L422.905,200.778L422.203,199.885L420.205,199.881L419.62,200.355L418.936,200.41L418.504,200.952L418.216,201.641L416.884,202.741L415.786,201.265L414.814,200.283L414.175,199.961L413.554,199.462L413.266,198.358L412.897,197.808L412.177,197.397L413.284,196.179L414.04,196.225L414.697,195.806L415.246,195.802L415.642,195.472L415.426,194.643L415.705,194.38ZM408.307,194.037L409.63,193.631L410.458,193.712L411.133,193.428L415.75,193.534L415.705,194.38L415.426,194.643L415.642,195.472L415.246,195.802L414.697,195.806L414.04,196.225L413.284,196.179L412.177,197.397L410.836,196.352L409.783,196.187L409.216,195.485L409.225,195.104L408.469,194.575ZM428.899,205.784L428.782,206.512L429.034,207.722L428.494,208.83L429.223,209.516L430.015,209.685L431.077,210.73L431.149,211.716L430.915,212.029L430.717,214.09L430.06,214.111L427.486,212.918L425.218,211.018L423.085,209.647L421.402,208.035L421.996,207.235L422.131,206.507L423.265,205.153L424.426,203.985L424.957,203.93L425.614,203.647L426.658,205.179L426.487,206.182L426.982,206.715L427.684,206.727L428.197,205.72ZM416.884,202.741L418.216,201.641L418.504,200.952L418.936,200.41L419.62,200.355L420.205,199.881L422.203,199.885L422.905,200.778L423.445,201.832L423.364,202.555L423.76,203.211L423.733,204.129L424.426,203.985L423.265,205.153L422.131,206.507L421.996,207.235L421.402,208.035L420.727,207.849L418.927,206.842L417.631,205.505L417.19,204.591ZM436.486,199.073L436.324,197.621L437.008,196.564L436.945,195.717L438.934,193.644L439.303,191.93L439.987,191.321L441.193,191.655L442.237,191.147L442.579,190.504L444.523,189.383L445,188.604L447.331,187.563L448.708,187.208L449.338,187.69L450.941,187.678L450.743,188.888L451.076,190.026L452.48,191.659L452.561,192.87L455.441,193.437L455.387,195.15L454.838,195.895L453.614,196.132L453.11,197.224L452.246,197.507L450.059,197.452L448.906,197.253L448.096,197.66L446.989,197.478L442.651,197.592L442.588,199.014L442.93,200.892L441.22,200.249L440.05,200.342L439.177,200.973L438.052,200.444L437.611,199.619ZM518.432,211.915L517.613,212.182L516.011,212.122L514.13,211.86L513.194,212.076L512.825,212.681L512.015,212.757L511.025,212.228L508.244,213.476L507.101,213.223L506.759,213.417L506.012,214.928L504.149,214.441L502.322,214.192L500.729,213.269L498.668,212.423L497.327,213.227L496.355,214.496L496.13,216.24L494.528,216.1L492.836,215.681L491.342,217.005L490.028,219.333L489.767,218.605L489.659,217.467L488.516,216.663L487.589,215.372L487.382,214.475L486.194,213.168L486.401,212.423L486.149,211.369L486.338,209.431L486.941,208.978L488.201,206.444L490.262,206.258L490.73,205.615L491.144,205.661L491.765,206.228L494.915,205.272L495.977,204.299L497.282,203.423L497.03,202.543L497.732,202.314L500.153,202.466L502.502,201.311L504.311,198.582L505.58,197.571L507.164,197.143L507.443,198.214L508.883,199.775L508.892,200.795L508.487,201.836L508.649,202.614L509.513,203.334L511.421,204.426L512.789,205.437L512.807,206.249L514.49,207.553L515.534,208.632L516.164,210.134L518.036,211.124ZM496.13,216.24L495.986,217.75L495.239,219.087L494.744,220.644L494.438,222.862L494.564,224.279L494.159,225.147L494.096,226.061L493.808,226.86L492.161,228.066L491.018,229.353L489.929,231.781L490.019,233.838L489.38,234.638L487.931,235.861L486.455,237.426L485.519,236.982L485.366,236.275L483.998,236.25L483.143,237.206L482.486,236.952L481.55,236.093L480.794,236.516L479.786,237.595L477.734,234.947L479.642,233.567L478.697,231.913L479.552,231.286L481.235,230.978L481.442,229.873L482.774,231.071L484.979,231.176L485.744,229.996L486.068,228.333L485.789,226.382L484.61,224.901L485.69,222.007L485.069,221.512L483.206,221.715L482.504,220.424L482.693,219.333L485.843,219.43L487.868,220.09L489.848,220.683L490.028,219.333L491.342,217.005L492.836,215.681L494.528,216.1ZM478.193,219.345L479.381,219.185L480.902,219.519L482.378,219.197L482.693,219.333L482.504,220.424L483.206,221.715L485.069,221.512L485.69,222.007L484.61,224.901L485.789,226.382L486.068,228.333L485.744,229.996L484.979,231.176L482.774,231.071L481.442,229.873L481.235,230.978L479.552,231.286L478.697,231.913L479.642,233.567L477.734,234.947L475.169,232.425L473.513,230.36L471.992,227.779L472.073,226.949L472.622,226.149L473.225,224.33L473.729,222.477L474.575,222.329L478.211,222.354ZM474.125,219.29L478.193,219.345L478.211,222.354L474.575,222.329L473.729,222.477L473.261,222.096ZM526.847,245.851L527.891,246.486L528.89,246.904L530.483,247.328L531.896,248.077L533.075,249.194L533.714,251.314L533.291,251.991L532.787,254.017L533.264,256.091L532.481,256.958L531.716,259.281L533.039,259.929L525.452,261.989L525.686,263.771L523.796,264.114L522.365,265.108L522.068,265.975L521.168,266.17L518.999,268.227L517.613,269.847L516.767,269.902L515.957,269.614L513.158,269.339L512.708,269.153L512.69,268.946L511.709,268.383L510.089,268.239L508.037,268.806L506.408,267.245L504.716,265.201L504.833,257.246L510.044,257.276L509.828,256.417L510.197,255.477L509.756,254.305L510.044,253.095L509.783,252.316L510.647,252.38L510.782,253.159L511.961,253.095L513.545,253.328L514.382,254.462L516.38,254.813L517.91,254.022L518.468,255.333L520.385,255.68L521.312,256.747L522.338,258.122L524.246,258.143L524.039,255.448L523.355,255.9L521.609,254.927L520.934,254.483L521.24,251.974L521.681,249.016L521.123,247.912L521.834,246.316L522.509,246.016L525.866,245.597ZM531.896,248.077L534.353,248.542L534.848,249.236L535.703,250.4L536.396,253.802L535.703,255.702L536.396,258.951L537.269,258.913L538.169,259.721L539.213,261.528L539.429,264.744L538.349,265.269L537.584,267.004L535.955,265.459L535.766,263.695L536.297,262.535L536.153,261.532L535.163,260.902L534.47,261.13L533.039,259.929L531.716,259.281L532.481,256.958L533.264,256.091L532.787,254.017L533.291,251.991L533.714,251.314L533.075,249.194ZM536.396,253.802L538.277,253.599L541.283,254.301L541.94,253.988L543.677,253.92L544.568,253.171L546.071,253.214L548.798,252.24L550.788,250.793L551.193,251.914L551.094,254.403L551.4,256.599L551.499,260.504L551.94,261.731L551.193,263.517L550.221,265.252L548.627,266.801L546.341,267.753L543.524,268.967L540.707,271.65L539.744,272.107L537.998,273.884L536.963,274.459L536.756,276.241L537.944,278.136L538.43,279.6L538.466,280.349L538.907,280.227L538.835,282.677L538.43,283.84L539.015,284.268L538.646,285.304L537.602,286.197L535.541,287.039L532.535,288.393L531.437,289.32L531.653,290.369L532.292,290.539L532.076,291.855L530.177,291.833L529.961,290.729L529.592,289.608L529.385,288.711L529.826,285.922L529.178,284.149L527.981,280.629L530.609,277.789L531.275,275.987L531.653,275.763L531.932,274.29L531.527,273.55L531.635,271.679L532.121,269.949L532.121,266.784L530.816,265.98L529.628,265.798L529.088,265.18L527.936,264.651L525.848,264.702L525.686,263.771L525.452,261.989L533.039,259.929L534.47,261.13L535.163,260.902L536.153,261.532L536.297,262.535L535.766,263.695L535.955,265.459L537.584,267.004L538.349,265.269L539.429,264.744L539.213,261.528L538.169,259.721L537.269,258.913L536.396,258.951L535.703,255.702ZM530.177,291.833L529.673,292.946L528.206,293.213L526.712,291.859L526.694,290.996L527.378,290.056L527.612,289.328L528.332,289.151L529.592,289.608L529.961,290.729ZM482.486,236.952L481.577,237.477L481.172,238.12L481.091,239.212L480.452,239.474L479.786,237.595L480.794,236.516L481.55,236.093ZM480.803,240.249L481.838,239.914L482.558,239.961L483.44,239.66L490.82,239.694L491.432,241.556L492.152,243.054L492.728,243.862L493.682,245.17L495.338,244.971L496.157,244.62L497.543,244.971L497.921,244.345L498.542,242.889L500.09,242.792L500.225,242.356L501.503,242.347L501.287,243.249L504.32,243.227L504.365,244.801L504.869,245.766L504.5,247.273L504.689,248.809L505.526,249.735L505.391,252.71L506.003,252.481L507.092,252.545L508.64,252.168L509.783,252.316L510.044,253.095L509.756,254.305L510.197,255.477L509.828,256.417L510.044,257.276L504.833,257.246L504.716,265.201L506.408,267.245L508.037,268.806L503.447,269.826L497.39,269.475L495.662,268.273L485.528,268.383L485.15,268.557L483.656,267.427L482.036,267.355L480.542,267.778L479.336,268.256L479.102,266.682L479.444,264.486L480.308,262.197L480.443,261.122L481.253,258.871L481.847,257.843L483.278,256.209L484.088,255.096L484.349,253.243L484.214,251.826L483.467,250.933L482.801,249.418L482.189,247.916L482.324,247.4L483.089,246.405L482.333,243.993L481.82,242.318L480.569,240.735ZM526.172,231.033L526.316,232.018L526.856,232.585L526.883,233.398L526.262,233.923L525.29,235.226L524.381,236.131L523.346,236.25L523.193,233.233L522.563,232.099L524.084,232.293L524.849,230.872ZM539.303,143.227L538.862,144.014L537.962,143.667L537.44,145.334L538.061,145.613L537.422,145.956L537.314,146.616L538.493,146.278L538.556,147.251L537.305,151.245L537.062,150.598L535.667,146.95L536.387,146.13L536.216,145.986L536.882,144.818L537.386,142.931L537.746,142.3L537.818,142.275L538.655,142.279L538.88,141.839L539.555,141.805L539.591,142.829L539.249,143.21ZM539.555,141.805L538.88,141.839L538.655,142.279L537.818,142.275L538.709,140.235L539.951,138.475L539.996,138.386L541.121,138.517L541.526,139.495L540.167,140.438ZM573.855,256.175L574.521,257.238L575.142,258.888L575.547,261.896L576.195,263.064L575.943,264.266L575.502,265.002L574.656,263.534L574.179,264.274L574.656,266.128L574.44,267.186L573.747,267.765L573.585,269.881L572.604,272.796L571.371,276.241L569.823,280.98L568.869,284.454L567.744,287.352L565.71,287.945L563.523,289.003L562.083,288.364L560.103,287.471L559.41,286.151L559.248,283.933L558.366,281.94L558.132,280.142L558.582,278.34L559.734,277.908L559.743,277.074L560.94,275.183L561.165,273.588L560.58,272.403L560.112,270.829L559.905,268.527L560.778,267.126L561.12,265.54L562.362,265.446L563.757,264.934L564.684,264.482L565.782,264.452L567.204,263.026L569.265,261.486L570.012,260.229L569.67,259.159L570.732,259.459L572.109,257.724L572.163,256.218L572.991,255.101ZM538.493,146.278L537.314,146.616L537.422,145.956L538.061,145.613L537.44,145.334L537.962,143.667L538.862,144.014L538.862,145.546ZM408.217,191.012L410.935,190.94L411.502,190.348L412.294,190.31L413.284,190.923L414.058,190.936L414.886,190.517L415.39,191.236L414.31,191.799L413.221,191.752L412.15,191.228L411.223,191.803L410.773,191.824L410.17,192.176L407.893,192.121ZM473.702,149.231L472.64,144.742L471.101,143.735L471.074,143.129L469.031,141.64L468.815,139.757L470.354,138.361L470.939,136.3L470.543,133.918L471.056,132.636L473.774,131.624L475.529,131.925L475.448,133.19L477.572,132.272L477.752,132.75L476.501,133.977L476.483,135.132L477.347,135.754L477.023,137.916L475.376,139.173L475.853,140.536L477.14,140.578L477.77,141.767L478.724,142.156L478.58,144.077L477.365,144.797L476.591,145.596L474.872,146.561L475.142,147.594L474.926,148.651ZM428.287,156.509L428.341,156.027L428.332,155.858L428.314,152.896L432.355,151.051L434.848,150.67L436.891,149.997L437.854,148.749L440.77,147.759L440.878,145.905L442.327,145.689L443.461,144.763L446.728,144.344L447.187,143.371L446.53,142.842L445.666,140.201L445.513,138.682L444.577,137.079L446.98,135.712L449.68,135.28L451.256,134.248L453.668,133.486L457.907,133.042L462.038,132.839L463.298,133.207L465.656,132.225L468.329,132.204L469.346,132.784L471.056,132.636L470.543,133.918L470.939,136.3L470.354,138.361L468.815,139.757L469.031,141.64L471.074,143.129L471.101,143.735L472.64,144.742L473.702,149.231L474.512,151.44L474.647,152.599L474.206,154.639L474.395,155.781L474.071,157.148L474.287,158.718L473.297,159.763L474.773,161.587L474.872,162.657L475.763,164.054L476.933,163.593L478.904,164.756L480.002,166.322L471.434,171.086L464.198,175.999L460.67,177.112L457.898,177.357L457.871,175.766L456.71,175.36L455.153,174.645L454.559,173.473L446.125,168.019L437.692,162.564ZM538.862,144.014L539.303,143.227L542.084,144.217L546.98,141.551L547.988,144.598L547.511,144.974L542.507,146.227L545,148.728L544.172,149.155L543.758,149.989L541.85,150.336L541.256,151.237L540.176,152.007L537.386,151.609L537.305,151.245L538.556,147.251L538.493,146.278L538.862,145.546ZM578.949,164.388L579.39,164.265L579.489,164.951L581.442,164.557L583.512,164.621L585.024,164.697L586.734,163.004L588.597,161.401L590.181,159.86L590.649,160.715L590.991,162.687L589.713,162.7L589.506,164.325L589.956,164.672L588.822,165.167L588.813,166.186L588.084,167.223L588.021,168.23L587.517,168.759L580.002,167.498L579.048,164.964ZM577.023,163.114L576.861,161.295L577.536,159.983L578.22,159.712L578.976,160.495L579.021,161.959L578.472,163.432L577.779,163.609ZM569.94,150.061L570.462,151.165L570.237,151.736L571.038,153.619L569.274,153.687L568.653,152.494L566.421,152.252L568.257,149.853ZM547.988,144.598L546.98,141.551L552.516,138.953L553.461,135.928L553.227,134.104L554.595,133.486L555.873,131.925L556.944,131.535L559.86,131.861L560.733,132.496L561.93,132.073L563.55,135.056L565.188,135.805L565.377,137.265L564.126,138.128L563.541,140.079L565.278,142.457L568.338,143.828L569.625,145.728L569.211,147.539L570.012,147.539L570.039,148.867L571.416,150.183L569.94,150.061L568.257,149.853L566.421,152.252L561.777,152.054L554.721,147.027L551.004,145.275ZM588.021,168.23L588.084,167.223L588.813,166.186L588.822,165.167L589.956,164.672L589.506,164.325L589.713,162.7L590.991,162.687L592.116,164.396L593.511,165.302L595.338,165.632L596.823,166.085L597.948,167.519L598.623,168.349L599.523,168.666L599.514,169.225L598.605,170.714L598.209,171.416L597.156,172.216L596.22,173.926L595.086,173.794L594.564,174.391L594.168,175.66L594.474,177.332L594.24,177.637L593.088,177.628L591.522,178.563L591.279,179.782L590.712,180.311L589.155,180.29L588.174,180.92L588.183,181.927L586.977,182.625L585.6,182.388L583.926,183.23L582.774,183.374L581.955,181.627L580.002,177.501L587.499,175L589.164,169.999ZM590.649,160.715L590.181,159.86L590.901,159.01L591.216,159.226L590.982,160.258ZM868.041,264.731L869.616,266.166L868.788,266.496L867.951,265.4ZM866.979,264.173L866.628,263.483L866.574,261.566L867.771,262.336L868.176,264.351L867.501,264.037ZM706.462,194.533L705.868,191.516L707.47,189.434L710.701,188.96L713.05,189.315L715.111,190.297L716.245,188.575L718.459,189.493L719.035,191.16L718.729,194.156L714.526,196.081L715.624,197.596L712.996,197.778L710.836,198.785L708.739,198.417L707.731,197.118ZM713.05,189.315L710.701,188.96L707.47,189.434L705.868,191.516L706.462,194.533L704.221,193.386L702.079,193.432L702.448,191.469L700.243,191.482L700.045,194.232L698.695,197.884L697.885,200.093L698.056,201.904L699.685,201.98L700.702,204.26L701.152,206.427L702.547,207.857L704.059,208.149L705.355,209.444L704.536,210.472L702.889,210.773L702.691,209.486L700.648,208.395L700.216,208.839L699.226,207.878L698.803,206.643L697.471,205.229L696.256,204.045L695.851,205.513L695.374,204.125L695.644,202.564L696.382,200.169L697.597,197.6L698.965,195.269L697.993,192.988L698.029,191.829L697.741,190.432L696.076,188.444L695.482,187.191L696.346,186.73L697.255,184.555L696.238,182.905L694.645,181.081L693.439,178.885L694.492,178.432L695.635,175.728L697.399,175.618L698.857,174.535L700.288,173.955L701.368,174.725L701.512,176.227L703.204,176.342L702.592,178.978L702.646,181.221L705.283,179.727L706.03,180.167L707.497,180.095L708.001,179.228L709.891,179.397L711.79,181.428L711.952,183.895L713.968,186.074L713.86,188.19ZM718.459,189.493L716.245,188.575L715.111,190.297L713.05,189.315L713.86,188.19L713.968,186.074L711.952,183.895L711.79,181.428L709.891,179.397L708.001,179.228L707.497,180.095L706.03,180.167L705.283,179.727L702.646,181.221L702.592,178.978L703.204,176.342L701.512,176.227L701.368,174.725L700.288,173.955L700.819,173.033L702.952,171.408L703.177,171.996L704.509,172.064L704.131,169.203L705.427,168.839L706.885,170.811L708.01,173.084L711.088,173.105L712.06,175.284L710.458,175.94L709.738,176.837L712.735,178.33L714.814,181.288L716.389,183.489L718.279,185.228L718.909,186.996ZM700.288,173.955L698.857,174.535L697.399,175.618L695.635,175.728L694.492,178.432L693.439,178.885L694.645,181.081L696.238,182.905L697.255,184.555L696.346,186.73L695.482,187.191L696.076,188.444L697.741,190.432L698.029,191.829L697.993,192.988L698.965,195.269L697.597,197.6L696.382,200.169L696.139,198.311L696.913,196.399L696.067,194.918L696.274,192.193L695.257,190.898L694.447,187.906L693.997,184.75L692.908,182.676L691.261,183.933L688.426,185.714L687.022,185.49L685.474,184.906L686.338,181.809L685.816,179.465L683.854,176.583L684.16,175.682L682.693,175.36L680.92,173.325L680.758,171.311L681.631,171.691L681.685,169.897L682.918,169.305L682.648,168.243L683.215,167.392L683.314,164.803L685.267,165.374L686.383,163.313L686.509,162.095L687.886,159.996L687.814,158.566L691.045,156.839L692.836,157.292L692.629,155.752L693.502,155.295L693.322,154.347L694.78,154.161L695.617,155.633L696.706,156.23L696.778,158.142L696.679,160.203L694.312,162.289L694.015,165.255L696.652,164.841L697.246,167.143L698.83,167.629L698.101,169.703L699.955,170.642L701.044,171.103L702.871,170.375L702.952,171.408L700.819,173.033ZM710.836,198.785L712.996,197.778L715.624,197.596L714.526,196.081L718.729,194.156L719.035,191.16L718.459,189.493L718.909,186.996L718.279,185.228L716.389,183.489L714.814,181.288L712.735,178.33L709.738,176.837L710.458,175.94L712.06,175.284L711.088,173.105L708.01,173.084L706.885,170.811L705.427,168.839L706.768,168.226L708.757,168.239L711.196,167.951L713.32,166.618L714.526,167.557L716.812,168.014L716.416,169.453L717.604,170.469L720.124,171.12L716.785,173.257L714.706,175.618L714.157,177.353L716.065,179.989L718.405,183.256L720.673,184.8L722.194,186.81L723.337,191.435L723.004,195.832L720.916,197.478L718.054,199.09L716.011,201.172L712.897,203.499L711.988,201.899L712.69,200.203ZM776.951,119.451L776.951,119.451L776.951,119.451ZM776.6,119.011L776.951,119.451L775.997,119.298L774.917,120.145L774.17,120.999L774.26,122.793L772.973,123.343L772.523,123.788L771.587,124.524L769.922,124.934L768.833,125.607L768.752,126.691L768.464,126.966L769.463,127.372L770.876,128.468L770.516,129.073L769.454,129.238L767.681,129.361L766.709,130.486L765.593,130.397L765.44,130.626L764.225,130.152L763.919,130.621L763.19,130.829L763.1,130.355L762.452,130.126L761.777,129.729L762.461,128.629L763.055,128.337L762.83,127.88L763.469,126.53L763.307,126.124L761.84,125.848L760.661,125.18L762.704,123.576L765.458,122.231L767.177,120.458L768.356,121.24L770.525,121.334L770.129,120.013L773.99,118.939L774.989,117.538ZM765.44,130.626L765.593,130.397L766.709,130.486L767.681,129.361L769.454,129.238L770.516,129.073L770.876,128.468L773.036,131.417L773.648,133.038L773.675,135.919L772.73,137.294L770.462,137.773L768.464,138.809L766.214,139.025L765.935,137.663L766.394,135.788L765.296,133.186L767.15,132.767ZM669.382,101.755L672.01,101.323L676.78,99.17L680.587,97.993L682.765,98.763L685.366,98.797L687.04,99.965L689.533,100.058L693.151,100.684L695.581,98.945L694.564,97.473L697.156,94.883L699.955,95.916L702.223,96.208L705.166,96.851L705.643,98.725L709.189,99.775L711.556,99.313L714.715,98.983L717.226,99.313L719.674,100.515L721.186,101.793L723.508,101.768L726.658,102.174L728.953,101.556L732.247,101.141L735.91,99.381L737.404,99.648L738.718,100.485L741.697,100.278L740.482,102.165L738.709,104.662L739.357,105.682L740.77,105.369L743.236,105.758L745.162,104.831L747.169,105.631L749.428,107.378L749.158,108.267L747.187,107.988L743.551,108.318L741.796,109.029L739.96,110.683L736.153,111.652L733.66,112.977L731.086,112.469L729.682,112.245L728.368,113.857L729.169,114.817L729.574,115.642L727.828,116.484L726.028,117.822L723.112,118.702L719.359,118.795L715.327,119.662L712.411,121.008L711.304,120.229L708.28,120.233L704.581,118.714L702.115,118.342L698.794,118.689L693.628,118.126L690.874,118.185L689.407,116.7L688.264,114.398L686.725,114.119L683.701,112.562L680.335,112.211L677.365,111.783L676.465,110.7L677.428,107.78L675.7,105.766L672.136,104.827L670.039,103.502ZM693.322,154.347L693.502,155.295L692.629,155.752L692.836,157.292L691.045,156.839L687.814,158.566L687.886,159.996L686.509,162.095L686.383,163.313L685.267,165.374L683.314,164.803L683.215,167.392L682.648,168.243L682.918,169.305L681.685,169.897L680.362,165.932L679.678,165.941L679.264,167.536L677.896,166.241L678.67,164.82L679.786,164.676L680.938,162.56L679.498,162.133L677.185,162.167L674.8,161.824L674.584,160.089L673.387,159.962L671.407,158.883L670.525,160.58L672.325,161.904L670.768,162.835L670.21,163.745L671.749,164.418L671.326,165.924L672.19,167.803L672.577,169.859L672.226,170.773L670.525,170.744L667.438,171.26L667.582,173.143L666.25,174.62L662.65,176.304L659.851,179.244L657.97,180.823L655.486,182.46L655.477,183.607L654.235,184.225L651.976,185.122L650.815,185.253L650.059,187.157L650.581,190.411L650.716,192.485L649.653,194.858L649.644,199.107L648.348,199.229L647.214,201.133L647.97,201.959L645.693,202.669L644.856,204.366L643.848,205.086L641.481,202.75L640.329,199.251L639.366,196.729L638.493,195.548L637.161,193.145L636.54,190.018L636.108,188.456L633.831,185.025L632.796,180.18L632.049,176.981L632.058,173.951L631.572,171.611L627.936,173.105L626.172,172.809L622.914,169.779L624.111,168.873L623.373,167.892L620.439,165.772L622.104,164.1L627.612,164.109L627.108,161.963L625.704,160.694L625.425,158.769L623.787,157.647L626.541,155.028L629.448,155.219L632.058,152.595L633.624,150.061L636.054,147.551L636.018,145.77L638.142,144.323L636.126,143.087L635.262,141.395L634.371,139.207L635.604,138.128L639.393,138.737L642.183,138.365L644.595,136.266L647.277,139.194L647.025,141.234L648.024,142.516L647.943,143.79L646.143,143.455L646.845,146.21L649.302,147.792L652.777,149.54L651.193,150.674L650.221,153.014L652.642,153.962L655,155.185L658.258,156.59L661.687,156.911L663.127,158.185L665.062,158.422L668.068,159.006L670.147,158.963L670.435,157.973L670.111,156.386L670.3,155.307L671.83,154.783L672.037,156.75L672.091,157.254L674.359,158.202L675.934,157.812L678.04,157.977L680.083,157.906L680.263,156.37L679.246,155.57L681.262,155.257L683.53,153.399L686.419,151.808L688.516,152.422L690.298,151.368L691.468,152.921L690.622,153.97ZM681.685,169.897L681.631,171.691L680.758,171.311L680.92,173.325L680.209,172.021L680.065,170.748L679.588,169.542L678.544,168.086L676.24,167.989L676.465,169.017L675.682,170.409L674.62,169.902L674.251,170.359L673.549,170.083L672.577,169.859L672.19,167.803L671.326,165.924L671.749,164.418L670.21,163.745L670.768,162.835L672.325,161.904L670.525,160.58L671.407,158.883L673.387,159.962L674.584,160.089L674.8,161.824L677.185,162.167L679.498,162.133L680.938,162.56L679.786,164.676L678.67,164.82L677.896,166.241L679.264,167.536L679.678,165.941L680.362,165.932ZM679.246,155.57L680.263,156.37L680.083,157.906L678.04,157.977L675.934,157.812L674.359,158.202L672.091,157.254L672.037,156.75L673.693,154.893L675.043,154.258L676.825,154.838L678.148,154.897ZM670.3,155.307L670.111,156.386L670.435,157.973L670.147,158.963L668.068,159.006L665.062,158.422L663.127,158.185L661.687,156.911L658.258,156.59L655,155.185L652.642,153.962L650.221,153.014L651.193,150.674L652.777,149.54L653.812,148.943L655.819,149.714L658.339,151.343L659.752,151.698L660.589,152.9L662.533,153.395L664.558,154.491L667.384,155.066ZM644.595,136.266L642.183,138.365L639.393,138.737L635.604,138.128L634.371,139.207L635.262,141.395L636.126,143.087L638.142,144.323L636.018,145.77L636.054,147.551L633.624,150.061L632.058,152.595L629.448,155.219L626.541,155.028L623.787,157.647L625.425,158.769L625.704,160.694L627.108,161.963L627.612,164.109L622.104,164.1L620.439,165.772L618.612,165.137L617.865,163.343L615.93,161.439L611.322,161.908L607.263,161.955L603.744,162.306L604.689,159.399L608.289,158.109L608.082,156.958L606.885,156.551L606.822,154.351L604.428,153.251L603.42,151.74L602.187,150.429L606.372,151.702L608.874,151.33L610.368,151.647L610.872,151.101L612.618,151.321L615.867,150.281L615.957,148.152L617.343,146.739L619.206,146.743L619.485,146.041L621.393,145.715L622.32,145.948L623.292,145.245L623.157,143.743L624.219,142.237L625.812,141.602L624.822,139.952L627.207,140.028L627.891,139.127L627.783,138.166L629.034,137.117L628.746,135.873L628.152,134.815L629.619,133.723L632.301,133.198L635.172,132.911L636.441,132.449L637.899,132.166L639.744,133.334L640.482,135.255ZM616.299,131.595L617.685,131.612L619.575,132.136L620.34,132.441L622.149,131.641L622.986,132.124L623.796,130.977L625.29,131.028L625.677,130.664L625.938,129.653L627.018,128.785L628.368,129.352L628.098,130.118L628.854,130.236L628.62,132.335L629.61,133.156L630.483,132.627L631.59,132.382L633.147,131.26L634.875,131.447L637.449,131.451L637.899,132.166L636.441,132.449L635.172,132.911L632.301,133.198L629.619,133.723L628.152,134.815L628.746,135.873L629.034,137.117L627.783,138.166L627.891,139.127L627.207,140.028L624.822,139.952L625.812,141.602L624.219,142.237L623.157,143.743L623.292,145.245L622.32,145.948L621.393,145.715L619.485,146.041L619.206,146.743L617.343,146.739L615.957,148.152L615.867,150.281L612.618,151.321L610.872,151.101L610.368,151.647L608.874,151.33L606.372,151.702L602.187,150.429L604.455,148.161L604.248,146.553L602.358,146.13L602.16,144.543L601.341,142.546L602.412,141.179L601.323,140.811L602.007,138.991L603.024,135.877L605.58,136.825L607.461,136.49L607.983,135.356L609.954,134.98L611.367,134.218L611.862,132.221L613.968,131.739L614.364,130.846L615.543,131.514ZM619.575,132.136L620.979,129.606L620.439,127.744L618.603,127.152L619.251,126.047L621.339,126.166L622.527,124.786L623.328,123.178L626.667,122.599L626.145,123.758L626.505,124.452L627.531,124.389L626.622,125.159L623.895,124.744L623.661,126.183L626.37,125.988L629.457,126.801L634.191,126.424L634.821,128.734L635.64,128.485L637.161,129.052L637.071,130.025L637.449,131.451L634.875,131.447L633.147,131.26L631.59,132.382L630.483,132.627L629.61,133.156L628.62,132.335L628.854,130.236L628.098,130.118L628.368,129.352L627.018,128.785L625.938,129.653L625.677,130.664L625.29,131.028L623.796,130.977L622.986,132.124L622.149,131.641L620.34,132.441ZM627.405,119.336L627.963,118.24L629.61,117.885L633.723,118.748L634.11,117.271L635.532,116.755L639.096,117.805L639.996,117.53L644.145,117.597L647.853,117.86L649.113,118.757L650.653,119.125L650.302,119.692L646.359,121.046L645.468,122.036L642.264,122.332L641.319,123.932L638.673,123.593L636.945,124.084L634.551,125.265L634.902,125.848L634.191,126.424L629.457,126.801L626.37,125.988L623.661,126.183L623.895,124.744L626.622,125.159L627.531,124.389L629.439,124.634L632.634,122.836L629.673,121.52L627.891,122.142L626.046,121.198L628.152,119.582ZM581.253,120.542L582.36,119.709L585.195,119.188L586.887,119.891L588.642,121.85L589.92,121.727L592.737,121.693L592.332,120.437L594.465,119.573L596.571,118.122L599.937,119.442L600.207,121.435L601.161,121.947L603.87,121.833L604.707,122.29L605.94,124.867L608.793,126.593L610.422,127.77L613.041,128.992L616.362,130.063L616.299,131.595L615.543,131.514L614.364,130.846L613.968,131.739L611.862,132.221L611.367,134.218L609.954,134.98L607.983,135.356L607.461,136.49L605.58,136.825L603.024,135.877L602.808,133.77L600.945,133.681L598.083,131.468L596.094,131.193L593.322,129.928L591.549,129.695L590.451,130.16L588.777,130.088L587.004,131.519L584.808,132.001L584.34,130.236L584.7,127.621L582.756,126.775L583.395,125.061L581.739,124.918L582.288,122.81L584.646,123.424L586.842,122.624L585.024,121.122L584.304,119.692L582.288,120.331L582.036,122.163ZM571.416,150.183L570.039,148.867L570.012,147.539L569.211,147.539L569.625,145.728L568.338,143.828L565.278,142.457L563.541,140.079L564.126,138.128L565.377,137.265L565.188,135.805L563.55,135.056L561.93,132.073L560.562,130.071L561.057,129.297L560.274,126.428L561.984,125.717L562.38,126.661L563.649,127.816L565.359,128.146L566.268,128.074L569.211,126.229L570.147,126.043L570.885,126.779L570.03,128.015L571.587,129.322L572.208,129.2L573,131.045L575.367,131.565L577.104,132.818L580.659,133.249L584.565,132.589L584.808,132.001L587.004,131.519L588.777,130.088L590.451,130.16L591.549,129.695L593.322,129.928L596.094,131.193L598.083,131.468L600.945,133.681L602.808,133.77L603.024,135.877L602.007,138.991L601.323,140.811L602.412,141.179L601.341,142.546L602.16,144.543L602.358,146.13L604.248,146.553L604.455,148.161L602.187,150.429L603.42,151.74L604.428,153.251L606.822,154.351L606.885,156.551L608.082,156.958L608.289,158.109L604.689,159.399L603.744,162.306L599.037,161.549L596.31,160.973L593.493,160.652L592.431,157.584L591.234,157.14L589.308,157.588L586.788,158.798L583.737,157.969L581.208,156.048L578.805,155.337L577.131,152.963L575.286,149.629L573.945,150.035L572.352,149.206ZM539.303,143.227L539.249,143.21L539.591,142.829L539.555,141.805L540.167,140.438L541.526,139.495L541.121,138.517L539.996,138.386L539.762,136.474L540.374,135.445L541.04,134.899L541.715,134.349L541.85,132.957L542.669,133.444L545.423,132.746L546.746,133.22L548.807,133.211L551.688,132.272L553.029,132.314L555.873,131.925L554.595,133.486L553.227,134.104L553.461,135.928L552.516,138.953L546.98,141.551L542.084,144.217ZM566.268,128.074L565.359,128.146L564.342,126.699L564.351,126.314L563.244,126.322L562.506,125.65L561.984,125.717L561.003,124.99L559.14,124.367L559.383,123.149L558.96,122.269L562.434,121.879L562.947,122.535L563.901,122.971L563.397,123.597L564.729,124.452L564.027,125.252L565.089,125.929L566.205,126.339ZM477.572,77.86L478.67,76.417L480.749,74.704L481.577,71.767L479.984,70.498L479.831,67.18L481.451,64.836L483.926,64.878L484.799,63.888L483.89,63.033L487.769,59.517L490.271,56.746L491.918,54.964L494.321,54.973L494.987,53.58L499.694,53.982L500.063,52.336L501.611,52.235L504.95,53.458L508.847,55.159L508.919,59.009L509.756,59.983L505.454,60.689L503.033,62.437L503.42,63.964L499.451,65.974L494.618,68.128L492.8,71.649L494.582,73.409L496.967,74.797L494.672,77.615L492.071,78.199L491.117,82.396L489.704,84.74L486.671,84.499L485.249,86.48L482.36,86.594L481.559,84.233L479.471,81.393ZM520.439,84.575L523.076,85.206L523.427,85.824L524.741,85.527L527.189,86.124L527.432,87.296L526.892,87.969L528.458,89.607L529.475,90.064L529.331,90.516L531.014,90.956L531.734,91.621L530.762,92.167L528.746,92.082L528.26,92.315L528.854,93.144L529.466,94.748L527.315,94.896L526.55,95.442L526.388,96.703L525.389,96.461L523.139,96.58L522.482,95.996L521.546,96.432L520.601,96.068L518.639,96.017L515.849,95.421L513.32,95.222L511.385,95.281L510.017,95.958L508.82,96.055L508.766,94.942L508.001,93.783L509.495,93.271L509.513,92.277L508.82,91.325L508.712,90.22L511.124,90.237L513.842,89.293L514.418,87.884L516.47,87.08L516.236,85.963L517.757,85.54ZM529.466,94.748L530.402,94.845L531.032,94.278L531.788,94.405L534.38,94.164L535.982,95.577L535.352,96.085L535.559,96.859L537.557,96.982L538.448,98.065L538.394,98.556L541.562,99.436L543.479,99.038L545.027,100.21L546.485,100.185L550.176,100.997L550.203,101.73L549.185,103.041L549.743,104.421L549.347,105.254L546.926,105.436L545.639,106.134L545.558,107.243L543.56,107.446L541.895,108.254L539.555,108.386L537.404,109.316L537.53,110.658L537.152,110.582L536.828,110.087L536.027,109.989L534.245,109.452L533.588,110.07L533.246,109.799L529.358,109.168L529.187,108.233L526.874,108.542L525.947,109.917L524.012,111.766L522.878,111.339L521.699,111.741L520.583,111.28L521.213,111.009L521.654,110.15L522.338,109.354L522.158,108.906L522.68,108.707L522.923,109.05L524.399,109.126L525.065,108.94L524.597,108.686L524.768,108.314L523.895,107.679L523.535,106.634L522.626,106.223L522.806,105.377L521.681,104.704L520.646,104.611L518.81,103.833L517.145,104.078L516.551,104.446L515.489,104.446L514.868,105.034L513.023,105.271L512.168,105.656L511.007,105.047L509.405,105.034L507.857,104.759L506.777,105.297L506.606,104.624L505.211,103.943L505.706,102.935L506.399,102.284L506.939,102.432L506.3,101.306L508.568,99.229L509.81,98.937L510.071,98.234L508.82,96.055L510.017,95.958L511.385,95.281L513.32,95.222L515.849,95.421L518.639,96.017L520.601,96.068L521.546,96.432L522.482,95.996L523.139,96.58L525.389,96.461L526.388,96.703L526.55,95.442L527.315,94.896ZM508.712,90.22L508.82,91.325L509.513,92.277L509.495,93.271L508.001,93.783L508.766,94.942L508.82,96.055L510.071,98.234L509.81,98.937L508.568,99.229L506.3,101.306L506.939,102.432L506.399,102.284L504.023,101.323L502.223,101.679L501.044,101.421L499.559,101.958L498.299,101.069L497.273,101.412L497.129,101.26L495.986,100.028L494.123,99.876L493.889,99.093L492.17,98.814L491.801,99.461L490.442,98.945L490.595,98.256L488.732,98.04L487.544,97.232L486.518,95.636L486.716,94.773L486.095,93.436L485.186,92.547L485.879,91.879L485.303,90.609L487.004,89.873L490.91,88.718L494.06,87.872L496.553,88.295L496.742,88.904L499.154,88.934L502.232,89.217L506.831,89.179L508.109,89.45ZM492.449,104.691L492.26,105.711L490.856,105.72L491.333,106.261L490.505,107.869L490.028,108.292L487.841,108.352L486.581,108.919L484.52,108.728L480.938,108.081L480.38,107.213L477.914,107.645L477.626,108.123L476.105,107.768L474.827,107.7L473.702,107.243L474.08,106.629L473.99,106.189L474.737,106.05L476.006,106.744L476.357,106.084L478.562,106.189L480.353,105.741L481.55,105.817L482.333,106.329L482.567,105.906L482.207,104.277L483.107,103.959L483.989,102.809L485.843,103.612L487.256,102.588L488.138,102.402L490.073,103.164L491.252,103.037L492.404,103.507L492.197,103.824ZM505.211,103.943L506.606,104.624L506.777,105.297L505.247,105.817L504.068,107.514L502.556,109.211L500.549,109.68L498.992,109.57L497.075,110.226L496.139,110.603L494.078,110.12L492.206,109.05L491.414,108.741L490.928,107.895L490.505,107.869L491.333,106.261L490.856,105.72L492.26,105.711L492.449,104.691L493.718,105.33L494.645,105.605L496.742,105.297L496.94,104.797L497.939,104.721L499.154,104.332L499.424,104.493L500.594,104.179L501.188,103.591L502.007,103.439L504.68,104.201ZM516.551,104.446L517.145,104.078L518.81,103.833L520.646,104.611L521.681,104.704L522.806,105.377L522.626,106.223L523.535,106.634L523.895,107.679L524.768,108.314L524.597,108.686L525.065,108.94L524.399,109.126L522.923,109.05L522.68,108.707L522.158,108.906L522.338,109.354L521.654,110.15L521.213,111.009L520.583,111.28L520.133,110.137L520.403,109.071L520.322,107.975L518.882,106.486L518.081,105.432L517.307,104.691ZM520.583,111.28L521.699,111.741L522.878,111.339L524.012,111.766L524.066,112.41L522.851,112.951L522.095,112.714L521.393,115.731L519.926,115.469L518.108,114.559L515.165,115.143L513.923,115.778L510.251,115.647L508.334,115.257L507.362,115.439L506.642,114.411L506.183,113.975L506.768,113.556L506.147,113.243L505.364,113.806L503.906,113.078L503.708,112.046L502.187,111.457L501.908,110.662L500.549,109.68L502.556,109.211L504.068,107.514L505.247,105.817L506.777,105.297L507.857,104.759L509.405,105.034L511.007,105.047L512.168,105.656L513.023,105.271L514.868,105.034L515.489,104.446L516.551,104.446L517.307,104.691L518.081,105.432L518.882,106.486L520.322,107.975L520.403,109.071L520.133,110.137ZM516.236,85.963L516.47,87.08L514.418,87.884L513.842,89.293L511.124,90.237L508.712,90.22L508.109,89.45L506.831,89.179L506.624,88.544L506.894,87.859L505.787,87.461L503.168,87.025L502.637,84.922L505.499,84.157L509.693,84.317L512.15,84.068L512.501,84.588L513.833,84.749ZM518.216,81.313L519.422,81.888L519.638,83.103L520.439,84.575L517.757,85.54L516.236,85.963L513.833,84.749L512.501,84.588L512.15,84.068L509.693,84.317L505.499,84.157L502.637,84.922L502.727,83.039L503.951,81.47L506.309,80.615L508.298,82.485L510.305,82.434L510.782,80.518L512.915,80.073L514.004,80.382L516.155,81.309ZM519.953,76.312L520.331,76.747L518.549,78.19L519.296,80.522L518.216,81.313L516.155,81.309L514.004,80.382L512.915,80.073L510.782,80.518L511.07,79.041L510.152,79.358L508.568,78.47L508.352,77.031L511.511,76.337L514.661,75.973L517.37,76.383ZM485.303,90.609L485.879,91.879L485.186,92.547L486.095,93.436L486.716,94.773L486.518,95.636L487.544,97.232L486.428,97.494L485.771,97.206L485.141,97.684L483.341,98.167L482.414,98.789L480.596,99.335L481.037,100.079L481.307,101.133L482.576,101.734L483.989,102.809L483.107,103.959L482.207,104.277L482.567,105.906L482.333,106.329L481.55,105.817L480.353,105.741L478.562,106.189L476.357,106.084L476.006,106.744L474.737,106.05L473.99,106.189L471.308,105.424L470.795,105.965L468.671,105.948L468.986,104.167L470.246,102.457L466.646,101.996L465.467,101.34L465.611,100.244L465.107,99.682L465.395,97.989L464.972,95.37L466.475,95.37L467.105,94.43L467.726,92.141L467.267,91.295L467.753,90.766L469.841,90.631L470.309,91.181L472.001,89.949L471.434,89.01L471.317,87.592L473.207,87.922L474.809,87.542L474.845,88.506L477.374,89.09L477.347,89.979L479.894,89.509L481.298,88.824L484.115,89.81ZM506.642,114.411L507.362,115.439L508.334,115.257L510.251,115.647L513.923,115.778L515.165,115.143L518.108,114.559L519.926,115.469L521.393,115.731L520.097,116.768L519.188,118.554L519.989,119.98L517.838,119.645L515.291,120.432L515.264,121.676L512.996,121.913L511.232,121.042L509.234,121.727L507.38,121.655L507.2,120.001L505.949,119.201L506.363,118.846L506.093,118.549L506.516,117.754L507.461,116.971L506.246,115.892L506.03,114.978ZM515.723,136.749L515.408,137.489L511.808,137.701L511.835,137.286L508.784,136.799L509.252,135.737L510.62,136.579L512.564,136.435L514.427,136.613L514.364,137.049ZM507.38,121.655L509.234,121.727L511.232,121.042L512.996,121.913L515.264,121.676L515.291,120.432L516.506,121.097L515.732,122.658L515.138,122.942L513.617,122.87L512.312,122.633L509.288,123.284L511.016,124.689L509.747,125.095L508.361,125.1L507.038,123.809L506.57,124.359L507.128,125.853L508.379,127.025L507.434,127.571L508.829,128.726L510.062,129.449L510.098,130.863L507.785,130.198L508.523,131.476L506.939,131.739L507.884,133.943L506.228,133.977L504.176,132.89L503.24,130.888L502.799,129.225L501.827,128.074L500.54,126.648L500.378,125.937L501.539,124.723L501.683,123.91L502.502,123.551L502.547,122.895L504.185,122.671L505.139,122.125L506.489,122.176L506.903,121.74ZM561.93,132.073L560.733,132.496L559.86,131.861L556.944,131.535L555.873,131.925L553.029,132.314L551.688,132.272L548.807,133.211L546.746,133.22L545.423,132.746L542.669,133.444L541.85,132.957L541.715,134.349L541.04,134.899L540.374,135.445L539.456,134.311L540.401,133.372L538.88,133.588L536.783,133.012L535.064,134.451L531.275,134.73L529.25,133.389L526.55,133.304L525.974,134.341L524.246,134.637L521.834,133.308L519.107,133.355L517.622,130.867L515.795,129.479L517.01,127.537L515.426,126.339L518.198,123.949L522.05,123.851L523.103,121.951L527.864,122.281L530.87,120.661L533.786,119.954L537.917,119.899L542.282,121.664L545.873,122.628L548.78,122.243L550.932,122.468L553.884,121.16L556.548,121.042L558.96,122.269L559.383,123.149L559.14,124.367L561.003,124.99L561.984,125.717L560.274,126.428L561.057,129.297L560.562,130.071ZM515.291,120.432L517.838,119.645L519.989,119.98L520.286,120.944L522.473,121.748L522.014,122.362L519.044,122.501L517.982,123.272L515.894,124.621L515.111,123.454L515.138,122.942L515.732,122.658L516.506,121.097ZM502.547,122.895L502.502,123.551L501.683,123.91L501.539,124.723L500.378,125.937L499.946,125.764L499.901,125.214L498.515,124.372L498.299,123.183L498.506,121.477L498.848,120.699L498.425,120.305L498.263,119.51L499.343,118.279L499.505,118.748L500.18,118.528L500.711,119.201L501.305,119.455L501.476,120.36L501.161,121.211L501.512,122.286ZM491.414,108.741L492.206,109.05L494.078,110.12L496.139,110.603L497.075,110.226L497.678,111.195L498.479,111.91L497.516,112.85L496.382,112.295L494.654,112.329L492.503,111.914L491.333,111.969L490.793,112.49L489.902,111.914L489.371,112.951L490.595,114.123L491.144,114.898L492.287,115.833L493.241,116.383L494.186,117.428L496.4,118.376L496.121,118.799L493.772,117.877L492.323,116.975L490.037,116.231L487.94,114.394L488.444,114.204L487.301,113.154L487.256,112.308L485.645,111.914L484.88,112.993L484.142,112.156L484.196,111.288L484.286,111.25L486.032,111.335L486.491,110.912L487.337,111.322L488.318,111.369L488.309,110.67L489.182,110.417L489.425,109.405ZM473.99,106.189L474.08,106.629L473.702,107.243L474.827,107.7L476.105,107.768L475.907,108.792L474.809,109.215L472.955,108.898L472.415,109.909L471.227,109.989L470.795,109.591L469.391,110.438L468.185,110.556L467.105,110.023L466.25,108.927L465.053,109.316L465.098,108.187L466.925,106.782L466.844,106.147L467.978,106.376L468.671,105.948L470.795,105.965L471.308,105.424ZM465.107,99.682L465.611,100.244L465.467,101.34L464.747,101.395L464.189,101.175L464.459,99.775ZM465.395,97.989L465.107,99.682L464.459,99.775L464.189,101.175L462.002,100.037L460.715,100.232L458.969,99.051L457.808,98.048L456.647,98.006L456.287,97.13L458.285,96.635L460.121,96.834L462.434,96.313L464.018,97.405ZM467.267,91.295L467.726,92.141L467.105,94.43L466.475,95.37L464.972,95.37L465.395,97.989L464.018,97.405L462.434,96.313L460.121,96.834L458.285,96.635L459.572,95.949L461.768,92.272L465.188,91.223ZM427.414,120.297L428.323,119.662L429.34,119.298L429.97,120.521L431.446,120.521L431.869,120.204L433.327,120.293L434.029,121.545L432.868,122.222L432.841,124.173L432.436,124.537L432.337,125.722L431.257,125.925L432.256,127.427L431.563,129.069L432.427,129.809L432.085,130.49L431.158,131.43L431.365,132.255L430.357,132.902L429.043,132.551L427.756,132.826L428.134,130.871L427.9,129.335L426.784,129.102L426.181,128.155L426.379,126.521L427.378,125.612L427.558,124.6L428.08,123.098L428.026,122.04L427.522,121.143ZM431.365,132.255L431.158,131.43L432.085,130.49L432.427,129.809L431.563,129.069L432.256,127.427L431.257,125.925L432.337,125.722L432.436,124.537L432.841,124.173L432.868,122.222L434.029,121.545L433.327,120.293L431.869,120.204L431.446,120.521L429.97,120.521L429.34,119.298L428.323,119.662L427.414,120.297L427.54,118.52L426.514,117.432L430.051,115.63L433.111,116.078L436.468,116.065L439.132,116.493L441.202,116.362L445.243,116.442L446.242,117.415L450.842,118.549L451.751,118.012L454.568,119.142L457.466,118.816L457.601,120.271L455.234,121.934L452.03,122.463L451.805,123.305L450.266,124.689L449.302,126.724L450.275,128.155L448.834,129.267L448.294,130.892L446.404,131.392L444.631,133.313L441.463,133.351L439.078,133.304L437.512,134.189L436.558,135.132L435.334,134.925L434.407,134.083L433.696,132.644ZM434.506,90.33L434.92,92.116L433.03,94.35L428.593,95.827L425.056,95.45L427.081,92.839L425.776,90.296L429.178,88.337L431.068,87.169L431.581,88.511L431.068,89.852L432.616,89.814ZM864.45,277.701L866.502,279.249L867.798,280.4L866.853,281.001L865.476,280.324L863.685,279.199L862.074,277.874L860.418,276.114L860.076,275.263L861.147,275.301L862.551,276.152L863.649,276.998ZM855.297,251.208L855.999,252.067L854.253,252.05L853.299,250.514L854.793,251.115ZM854.199,248.999L853.821,249.46L851.967,247.294L851.454,245.8L852.3,245.8L853.2,247.802ZM852.129,249.68L851.157,249.74L849.626,249.486L849.104,249.101L849.257,248.106L850.905,248.5L851.724,249.024ZM849.104,245.051L849.689,245.842L849.797,246.346L847.835,245.284L846.467,244.387L845.531,243.553L845.9,243.299L847.052,243.9ZM842.849,242.555L843.848,243.371L843.344,243.511L842.255,242.944L841.229,241.916L841.355,241.497ZM892.215,325.164L891.27,326.514L890.028,328.223L888.102,329.222L887.67,328.566L886.626,328.207L888.066,326.15L887.247,324.771L884.556,323.772L884.628,322.867L886.437,321.995L886.86,320.07L886.743,318.453L885.726,316.778L885.798,316.337L884.601,315.305L882.639,313.092L881.586,311.323L882.522,311.129L883.881,312.517L885.825,313.164L886.527,315.39L888.345,318.022L888.39,316.316L889.524,316.998L889.893,318.889L891.909,319.701L893.601,319.905L895.023,318.948L896.292,319.24L895.689,321.457L894.924,322.917L893.016,322.867L892.35,323.624L892.584,324.699ZM874.17,333.889L876.312,332.578L877.815,331.283L878.922,329.417L879.876,328.786L880.245,327.39L882,326.235L882.549,327.297L883.116,328.329L884.898,327.318L885.618,328.372L885.618,329.425L884.691,330.585L883.053,332.425L881.775,333.432L882.702,334.634L880.776,334.664L878.634,335.607L877.959,337.245L876.546,339.771L874.575,340.888L873.333,341.603L871.029,341.548L869.409,340.727L866.691,340.55L866.277,339.631L867.618,337.778L870.759,335.311L872.37,334.841ZM819.224,327.022L820.718,327.187L820.898,330.157L820.043,331.016L819.782,333.03L818.909,332.345L817.172,334.088L816.659,333.953L815.12,333.872L813.581,331.736L813.239,330.085L811.799,327.906L811.862,326.759L813.491,326.979L815.912,327.843L817.271,327.5ZM765.368,305.539L762.722,306.821L760.553,307.401L760.076,308.708L759.149,309.724L757.025,309.787L755.459,310.007L753.245,309.555L751.454,309.825L749.734,309.94L748.249,311.273L747.52,311.162L746.26,311.869L745.063,312.66L743.236,312.563L741.562,312.563L738.907,310.968L737.566,310.49L737.62,309.059L738.862,308.717L739.285,308.15L739.195,307.253L739.501,305.514L739.222,304.033L737.899,301.502L737.494,300.076L737.602,298.654L736.603,297.025L736.54,296.289L735.433,295.295L735.118,293.336L733.696,291.36L733.345,290.293L734.443,291.372L733.606,289.053L734.839,289.777L735.586,290.746L735.541,289.464L734.299,287.496L734.065,286.709L733.48,285.96L733.759,284.517L734.263,283.9L734.605,282.651L734.344,281.187L735.37,279.389L735.559,281.293L736.621,279.575L738.646,278.737L739.87,277.671L741.778,276.753L742.912,276.558L743.605,276.867L745.576,275.936L747.088,275.657L747.466,275.111L748.132,274.882L749.509,274.942L752.138,274.21L753.497,273.101L754.136,271.764L755.603,270.495L755.72,269.496L755.783,268.138L757.529,266.013L758.582,268.171L759.653,267.672L758.762,266.492L759.545,265.277L760.643,265.819L760.949,263.919L762.317,262.688L762.92,261.702L764.18,261.274L764.216,260.576L765.314,260.868L765.359,260.242L766.457,259.882L767.663,259.544L769.508,260.69L770.903,262.171L772.46,262.188L774.053,262.425L773.522,261.05L774.719,259.049L775.853,258.393L775.457,257.771L776.546,256.341L778.058,255.46L779.336,255.757L781.442,255.287L781.397,254.009L779.561,253.184L780.893,252.82L782.549,253.442L783.881,254.466L785.987,255.105L786.698,254.851L788.246,255.621L789.704,254.906L790.649,255.122L791.234,254.644L792.377,255.879L791.711,257.216L790.766,258.228L789.902,258.312L790.19,259.311L789.461,260.559L788.57,261.791L788.75,262.493L790.739,263.877L792.665,264.676L793.952,265.54L795.761,267.021L796.463,267.016L797.768,267.655L798.155,268.43L800.54,269.276L802.187,268.421L802.682,267.08L803.186,265.971L803.492,264.6L804.257,262.611L803.906,261.401L804.086,260.678L803.798,259.243L804.131,257.36L804.608,256.853L804.221,256.019L804.824,254.694L805.292,253.319L805.355,252.608L806.291,251.669L806.993,252.892L807.164,254.462L807.794,254.762L807.893,255.816L808.802,257.085L808.991,258.503L808.901,259.408L809.801,261.372L811.412,260.428L812.24,261.486L813.437,262.463L813.176,263.572L813.716,265.713L814.094,266.961L814.724,267.266L815.399,269.403L815.156,270.702L815.966,272.394L818.675,273.702L820.448,274.891L822.122,275.978L821.789,276.584L823.22,278.153L824.192,280.857L825.191,280.307L826.208,281.39L826.82,281.005L827.252,283.654L829.025,285.19L830.186,286.146L832.139,288.169L832.841,290.179L832.904,291.605L832.733,293.149L833.921,295.274L833.777,297.487L833.345,298.646L832.67,300.876L832.724,302.31L832.229,304.1L831.122,306.377L829.277,307.604L828.359,309.542L827.522,310.777L826.784,312.935L825.821,314.179L825.191,316.05L824.867,317.772L824.993,318.563L823.562,319.431L820.763,319.524L818.45,320.548L817.307,321.517L815.795,322.591L813.725,321.483L812.195,321.043L812.582,319.74L811.214,320.213L809.027,322.024L806.867,321.347L805.445,320.95L804.014,320.772L801.593,320.048L799.982,318.508L799.514,316.608L798.938,315.347L797.705,314.332L795.302,314.031L796.121,312.817L795.518,310.964L794.294,312.69L792.071,313.151L793.385,311.768L793.763,310.325L794.726,309.102L794.528,307.248L792.494,309.381L790.928,310.236L789.974,312.225L788.021,311.196L788.102,309.872L786.536,308.057L785.213,307.122L785.681,306.542L782.477,305.027L780.722,304.955L778.319,303.741L773.837,303.978L770.606,304.87L767.753,305.704ZM654.469,206.194L654.091,208.797L653.047,209.507L650.869,210.079L649.68,208.09L649.239,204.497L650.374,200.44L652.102,201.827L653.263,203.588ZM723.688,179.507L721.636,178.732L721.564,176.579L722.797,175.449L725.533,174.746L726.964,174.806L727.522,175.762L726.424,176.862L725.848,178.305ZM650.653,119.125L650.455,117.699L652.165,117.047L649.914,112.706L654.865,111.707L656.152,111.153L657.952,106.676L662.911,107.497L664.306,106.367L664.423,103.862L666.493,103.625L668.401,101.962L669.382,101.755L670.039,103.502L672.136,104.827L675.7,105.766L677.428,107.78L676.465,110.7L677.365,111.783L680.335,112.211L683.701,112.562L686.725,114.119L688.264,114.398L689.407,116.7L690.874,118.185L693.628,118.126L698.794,118.689L702.115,118.342L704.581,118.714L708.28,120.233L711.304,120.229L712.411,121.008L715.327,119.662L719.359,118.795L723.112,118.702L726.028,117.822L727.828,116.484L729.574,115.642L729.169,114.817L728.368,113.857L729.682,112.245L731.086,112.469L733.66,112.977L736.153,111.652L739.96,110.683L741.796,109.029L743.551,108.318L747.187,107.988L749.158,108.267L749.428,107.378L747.169,105.631L745.162,104.831L743.236,105.758L740.77,105.369L739.357,105.682L738.709,104.662L740.482,102.165L741.697,100.278L744.694,101.222L748.222,99.643L748.195,98.543L750.455,95.89L751.85,95.09L751.814,93.711L750.446,93.114L752.507,91.87L755.612,91.422L758.933,91.354L762.668,92.099L764.864,93.017L766.412,95.539L767.348,96.614L768.221,98.15L769.148,100.6L773.495,101.399L776.456,103.177L777.464,105.525L781.271,105.529L783.431,104.543L787.562,103.803L786.248,106.054L785.285,106.968L784.421,109.706L782.747,112.139L779.705,111.699L777.563,112.579L778.22,114.72L777.86,117.673L776.582,117.741L776.6,119.011L774.989,117.538L773.99,118.939L770.129,120.013L770.525,121.334L768.356,121.24L767.177,120.458L765.458,122.231L762.704,123.576L760.661,125.18L757.169,125.903L755.333,127.076L752.633,127.757L753.965,126.597L753.443,125.624L755.423,123.944L754.1,122.633L751.922,123.517L749.095,125.256L747.556,126.868L745.108,126.991L743.83,128.155L745.153,129.847L747.196,130.258L747.277,131.379L749.257,132.111L752.057,130.325L754.28,131.299L755.891,131.362L756.296,132.674L752.759,133.372L751.589,134.722L749.158,135.974L747.88,137.726L750.572,139.101L751.553,141.56L753.074,143.849L754.775,145.77L754.73,147.627L753.164,148.309L753.758,149.642L755.234,150.42L754.847,152.455L754.208,154.436L752.813,154.66L750.986,157.368L748.96,160.647L746.638,163.631L743.2,165.937L739.726,168.044L736.909,168.332L735.379,169.44L734.515,168.628L733.102,169.872L729.61,171.124L726.964,171.505L726.109,174.146L724.723,174.294L724.066,172.478L724.66,171.514L721.303,170.714L720.124,171.12L717.604,170.469L716.416,169.453L716.812,168.014L714.526,167.557L713.32,166.618L711.196,167.951L708.757,168.239L706.768,168.226L705.427,168.839L704.131,169.203L704.509,172.064L703.177,171.996L702.952,171.408L702.871,170.375L701.044,171.103L699.955,170.642L698.101,169.703L698.83,167.629L697.246,167.143L696.652,164.841L694.015,165.255L694.312,162.289L696.679,160.203L696.778,158.142L696.706,156.23L695.617,155.633L694.78,154.161L693.322,154.347L690.622,153.97L691.468,152.921L690.298,151.368L688.516,152.422L686.419,151.808L683.53,153.399L681.262,155.257L679.246,155.57L678.148,154.897L676.825,154.838L675.043,154.258L673.693,154.893L672.037,156.75L671.83,154.783L670.3,155.307L667.384,155.066L664.558,154.491L662.533,153.395L660.589,152.9L659.752,151.698L658.339,151.343L655.819,149.714L653.812,148.943L652.777,149.54L649.302,147.792L646.845,146.21L646.143,143.455L647.943,143.79L648.024,142.516L647.025,141.234L647.277,139.194L644.595,136.266L640.482,135.255L639.744,133.334L637.899,132.166L637.449,131.451L637.071,130.025L637.161,129.052L635.64,128.485L634.821,128.734L634.191,126.424L634.902,125.848L634.551,125.265L636.945,124.084L638.673,123.593L641.319,123.932L642.264,122.332L645.468,122.036L646.359,121.046L650.302,119.692ZM754.442,164.016L752.939,168.023L751.868,170.075L750.554,167.964L750.266,166.11L751.733,163.652L753.74,161.76L754.883,162.505ZM476.105,107.768L477.626,108.123L477.914,107.645L480.38,107.213L480.938,108.081L484.52,108.728L484.241,109.96L484.844,111.022L482.855,110.658L480.821,111.546L480.956,112.786L480.65,113.497L481.469,114.771L483.818,116.032L485.078,118.097L487.859,120.111L489.812,120.098L490.424,120.648L489.722,121.147L491.963,122.053L493.799,122.806L495.941,124.109L496.202,124.579L495.734,125.472L494.348,124.304L492.17,123.894L491.126,125.51L492.926,126.437L492.629,127.744L491.585,127.892L490.253,130.033L489.209,130.228L489.218,129.462L489.731,128.121L490.271,127.588L489.299,126.14L488.534,124.879L487.499,124.566L486.761,123.487L485.15,123.035L484.07,122.028L482.216,121.867L480.263,120.737L477.977,119.112L476.276,117.673L475.502,115.198L474.26,114.91L472.226,114.085L471.074,114.424L469.625,115.583L468.59,115.765L468.878,114.682L467.519,114.364L466.871,112.431L467.744,111.669L467.006,110.73L467.105,110.023L468.185,110.556L469.391,110.438L470.795,109.591L471.227,109.989L472.415,109.909L472.955,108.898L474.809,109.215L475.907,108.792ZM486.905,129.64L488.804,129.424L487.904,131.392L488.273,132.166L487.751,133.448L485.834,132.509L484.565,132.238L481.082,130.968L481.424,129.682L484.349,129.911ZM471.776,122.751L473.027,121.977L474.521,123.75L474.17,127.059L473.036,126.898L472.019,127.731L471.074,127.071L470.975,124.054L470.399,122.624ZM474.809,87.542L473.207,87.922L471.317,87.592L470.3,86.205L470.228,83.649L470.642,82.976L471.362,82.227L473.558,82.07L474.44,81.381L476.447,80.674L476.366,81.96L475.628,82.773L475.925,83.475L477.284,83.852L476.672,84.795L475.925,84.525L474.125,86.323ZM480.929,84.724L481.721,85.976L480.227,87.999L477.608,86.59L477.257,85.549ZM434.506,90.33L432.616,89.814L431.068,89.852L431.581,88.511L431.068,87.169L433.165,87.068L435.847,88.612ZM442.264,91.49L442.273,91.49L442.633,90.038L440.959,88.498L440.923,88.464L437.89,88.024L437.296,87.347L438.205,86.23L437.377,85.54L436.036,86.721L435.883,84.313L434.623,83.039L435.532,80.454L437.476,78.423L439.474,78.622L442.489,78.415L439.816,81.118L442.363,80.776L445.099,80.788L444.451,82.824L442.201,85.066L444.784,85.227L444.982,85.489L447.214,88.439L448.924,88.841L450.464,91.688L451.175,92.674L454.208,93.152L453.902,94.752L452.624,95.484L453.623,96.775L451.373,98.086L448.033,98.061L443.776,98.751L442.606,98.26L440.959,99.428L438.646,99.144L436.891,100.1L435.559,99.601L439.222,96.973L441.463,96.436L441.445,96.432L437.539,96.017L436.828,95.023L439.447,94.248L438.079,92.899L438.547,91.261ZM413.725,58.861L413.149,60.478L415.975,62.183L412.726,64.091L405.517,65.805L403.357,66.258L400.072,65.89L393.097,65.098L395.554,63.994L390.109,62.771L394.537,62.289L394.429,61.552L389.182,60.973L390.874,59.344L394.663,58.975L398.56,60.668L402.358,59.31L405.499,60.016L409.576,58.684ZM566.016,120.348L566.718,120.432L568.437,121.951L569.535,122.121L569.967,121.486L571.461,120.479L572.775,121.795L574.044,123.568L575.214,123.686L575.979,124.359L573.927,124.558L573.486,126.5L573.054,127.376L572.145,127.96L572.208,129.2L571.587,129.322L570.03,128.015L570.885,126.779L570.147,126.043L569.211,126.229L566.268,128.074L566.205,126.339L565.089,125.929L564.027,125.252L564.729,124.452L563.397,123.597L563.901,122.971L562.947,122.535L562.434,121.879L563.046,121.473L564.909,122.188L566.25,122.341L566.592,122.044L565.368,120.695ZM565.359,128.146L563.649,127.816L562.38,126.661L561.984,125.717L562.506,125.65L563.244,126.322L564.351,126.314L564.342,126.699ZM549.887,116.412L550.194,116.116L552.309,116.544L555.99,116.95L559.392,118.147L559.824,118.613L561.345,118.219L563.676,118.744L564.441,119.768L566.016,120.348L565.368,120.695L566.592,122.044L566.25,122.341L564.909,122.188L563.046,121.473L562.434,121.879L558.96,122.269L556.548,121.042L553.884,121.16L554.262,120.094L553.632,118.389L552.192,117.466L550.806,117.178ZM752.084,193.238L750.806,191.334L752.948,191.427L753.821,192.328L753.155,194.486ZM756.467,200.046L757.097,199.348L757.367,197.795L758.744,197.647L758.348,199.331L760.193,196.919L759.959,199.301L759.059,200.126L758.276,201.705L757.493,202.445L755.954,200.715ZM765.944,203.964L766.196,205.623L766.34,207.028L765.494,209.313L764.576,206.765L763.406,208.035L764.207,209.876L763.496,211.048L760.553,209.596L759.851,207.785L760.607,206.6L759.023,205.416L758.24,206.452L757.061,206.355L755.216,207.751L754.802,207.019L755.783,204.912L757.358,204.21L758.717,203.266L759.599,204.4L761.507,203.715L761.912,202.598L763.676,202.534L763.532,200.6L765.557,201.785L765.764,203.042ZM746.26,201.709L742.939,204.083L744.163,202.331L745.963,200.791L747.466,199.06L748.78,196.576L749.221,198.616L747.574,199.991ZM755.846,179.439L755.432,180.476L756.287,182.266L755.63,184.343L754.154,185.173L753.767,187.187L754.325,189.18L755.648,189.455L756.755,189.159L759.878,190.547L759.635,191.905L760.454,192.506L760.193,193.657L758.249,192.43L757.322,191.118L756.683,192.036L755.09,190.538L752.813,190.906L751.571,190.356L751.697,189.324L752.48,188.685L751.733,188.109L751.409,189.011L750.176,187.572L749.806,186.484L749.707,184.089L750.716,184.915L750.977,181L751.787,178.737L753.308,178.741L754.847,179.452L755.612,178.804ZM755.099,196.462L754.712,195.269L756.206,196.043L757.799,196.039L757.754,197.084L756.593,198.146L755.009,198.899L754.919,197.736ZM763.757,194.592L764.459,197.384L762.533,196.72L762.578,197.562L763.19,199.102L762.002,199.665L761.903,197.905L761.147,197.774L760.76,196.263L762.227,196.462L762.191,195.514L760.67,193.606L763.064,193.661ZM700.216,208.839L700.648,208.395L702.691,209.486L702.889,210.773L704.536,210.472L705.355,209.444L705.931,209.681L707.407,211.187L708.451,212.863L708.595,214.547L708.334,215.685L708.577,216.544L708.757,218.021L709.639,218.711L710.62,220.924L710.575,221.766L708.802,221.935L706.435,220.082L703.474,218.097L703.186,216.824L701.737,215.152L701.395,213.083L700.495,211.72L700.765,209.897ZM744.703,214.657L742.534,214.234L739.663,214.234L738.799,217.077L737.836,217.945L736.549,221.423L734.515,221.956L732.148,221.254L730.951,221.474L729.493,222.739L727.9,222.557L726.289,223.069L724.579,221.656L724.156,219.984L725.992,220.839L727.918,220.374L728.422,218.258L729.493,217.784L732.49,217.242L734.281,215.266L735.514,213.684L736.648,214.983L737.17,214.128L738.367,214.208L738.511,212.613L738.628,211.382L740.554,209.643L741.814,207.688L742.822,207.679L744.109,208.945L744.226,210.032L745.873,210.73L747.952,211.479L747.772,212.461L746.098,212.584L746.548,213.807ZM738.628,211.382L738.511,212.613L738.367,214.208L737.17,214.128L736.648,214.983L735.514,213.684L736.504,212.749ZM484.52,108.728L486.581,108.919L487.841,108.352L490.028,108.292L490.505,107.869L490.928,107.895L491.414,108.741L489.425,109.405L489.182,110.417L488.309,110.67L488.318,111.369L487.337,111.322L486.491,110.912L486.032,111.335L484.286,111.25L484.844,111.022L484.241,109.96ZM521.483,52.336L521.114,54.088L524.939,55.755L522.635,57.638L525.542,60.486L523.859,62.627L526.109,64.489L525.092,66.118L528.791,67.832L527.846,69.105L525.524,70.548L520.178,73.743L515.642,73.942L511.241,74.856L507.173,75.385L505.724,74.018L503.303,73.201L503.861,70.739L502.646,68.483L503.843,67.024L506.111,65.454L511.826,62.746L513.491,62.221L513.239,61.163L509.756,59.983L508.919,59.009L508.847,55.159L504.95,53.458L501.611,52.235L503.114,51.575L505.895,52.895L509.153,52.772L511.835,53.377L514.22,52.269L515.453,50.437L519.332,49.59L522.536,50.585ZM506.399,102.284L505.706,102.935L505.211,103.943L504.68,104.201L502.007,103.439L501.188,103.591L500.594,104.179L499.424,104.493L499.154,104.332L497.939,104.721L496.94,104.797L496.742,105.297L494.645,105.605L493.718,105.33L492.449,104.691L492.197,103.824L492.404,103.507L492.755,102.957L493.862,102.999L494.717,102.741L494.78,102.508L495.266,102.39L495.428,101.823L496.004,101.713L496.391,101.264L497.129,101.26L497.273,101.412L498.299,101.069L499.559,101.958L501.044,101.421L502.223,101.679L504.023,101.323ZM487.544,97.232L488.732,98.04L490.595,98.256L490.442,98.945L491.801,99.461L492.17,98.814L493.889,99.093L494.123,99.876L495.986,100.028L497.129,101.26L496.391,101.264L496.004,101.713L495.428,101.823L495.266,102.39L494.78,102.508L494.717,102.741L493.862,102.999L492.755,102.957L492.404,103.507L491.252,103.037L490.073,103.164L488.138,102.402L487.256,102.588L485.843,103.612L483.989,102.809L482.576,101.734L481.307,101.133L481.037,100.079L480.596,99.335L482.414,98.789L483.341,98.167L485.141,97.684L485.771,97.206L486.428,97.494ZM541.076,188.943L540.806,187.944L541.886,184.271L542.129,182.608L542.921,181.843L544.757,181.432L546.026,180.006L547.475,182.9L548.168,185.194L549.536,186.412L552.948,188.774L554.334,190.195L555.693,191.638L556.476,192.497L557.7,193.25L556.953,193.86L555.882,193.644L555.027,192.836L554.001,191.372L552.885,190.568L552.246,189.704L550.068,188.702L548.348,188.672L547.745,188.147L546.278,188.735L544.766,187.601L543.983,189.468ZM804.707,127.046L802.403,129.564L802.439,132.145L801.503,134.142L801.935,135.395L800.63,137.155L797.435,138.331L793.043,138.483L789.479,141.34L787.805,140.379L787.697,138.509L783.35,139.059L780.389,140.239L777.464,140.286L780.002,142.127L778.328,146.375L776.717,147.424L775.502,146.455L776.123,144.2L774.539,143.472L773.522,141.759L775.889,140.988L777.194,139.419L779.714,138.124L781.541,136.419L786.518,135.67L789.191,136.182L791.81,131.739L793.475,132.932L797.147,130.431L798.569,129.462L800.135,126.403L799.712,123.593L800.765,122.011L803.42,121.554L804.788,125.019ZM811.529,115.096L813.302,114.039L813.86,116.844L810.152,117.53L807.956,120.013L804.032,118.304L802.664,121.037L799.892,121.075L799.541,118.592L800.783,116.666L803.447,116.527L804.176,113.07L804.923,111.123L807.857,113.726L809.774,114.563ZM780.929,141.34L782.315,139.85L783.737,140.138L784.763,139.089L786.599,139.626L786.914,140.485L785.51,141.995L784.484,141.196L783.197,141.775L782.54,143.24L780.911,142.529ZM304.581,275.441L305.319,276.833L305.157,280.227L307.794,280.705L308.82,280.214L310.503,280.891L310.971,281.64L311.205,283.929L311.502,284.894L312.429,285.004L313.365,284.598L314.265,285.051L314.265,286.426L313.923,287.907L313.437,289.35L313.032,291.554L310.764,293.471L308.784,293.873L305.976,293.488L303.456,292.811L305.913,289.011L305.553,287.907L302.979,286.929L299.928,285.08L297.885,284.704L293.286,280.624L294.276,277.629L294.339,276.283L295.536,274.083L299.892,273.355L302.214,273.393L304.545,274.671ZM580.002,177.501L581.955,181.627L582.774,183.374L580.965,184.043L580.479,185.156L580.425,186.006L577.932,187.06L573.936,188.228L571.695,189.992L570.597,190.132L569.85,189.984L568.383,191.02L566.79,191.503L564.693,191.63L564.063,191.774L563.514,192.434L562.857,192.616L562.47,193.25L561.237,193.195L560.436,193.534L558.708,193.407L558.06,191.947L558.132,190.58L557.718,189.844L557.232,187.995L556.512,186.967L557.016,186.844L556.755,185.702L557.061,185.219L556.953,184.132L558.042,183.332L557.79,182.278L558.456,181.051L559.482,181.699L560.157,181.474L563.046,181.415L563.496,181.665L565.917,181.919L566.871,181.792L567.501,182.625L568.671,182.206L570.462,179.583L572.793,178.457ZM537.386,151.609L540.176,152.007L541.256,151.237L541.85,150.336L543.758,149.989L544.172,149.155L545,148.728L542.507,146.227L547.511,144.974L547.988,144.598L551.004,145.275L554.721,147.027L561.777,152.054L566.421,152.252L568.653,152.494L569.274,153.687L571.038,153.619L572.019,155.777L573.252,156.348L573.675,157.224L575.385,158.278L575.529,159.306L575.286,160.14L575.601,160.982L576.321,161.68L576.654,162.501L577.023,163.114L577.779,163.609L578.472,163.432L578.949,164.388L579.048,164.964L580.002,167.498L587.517,168.759L588.021,168.23L589.164,169.999L587.499,175L580.002,177.501L572.793,178.457L570.462,179.583L568.671,182.206L567.501,182.625L566.871,181.792L565.917,181.919L563.496,181.665L563.046,181.415L560.157,181.474L559.482,181.699L558.456,181.051L557.79,182.278L558.042,183.332L556.953,184.132L556.62,183.065L555.873,182.312L555.675,181.314L554.388,180.417L553.056,178.322L552.345,176.282L550.617,174.565L549.5,174.154L547.844,171.772L547.556,170.033L547.664,168.552L546.233,165.78L545.063,164.803L543.713,164.286L542.885,162.852L543.02,162.289L542.327,160.994L541.598,160.436L540.626,158.574L539.096,156.56L537.827,154.842L536.576,154.855L536.972,153.479L537.08,152.608ZM328.35,420.117L329.619,420.117L333.345,419.579L337.116,420.117L340.194,421.196L341.274,422.715L341.571,423.79L341.67,425.063L337.8,425.85L333.732,426.485L329.034,427.073L323.796,427.564L317.874,427.416L314.589,426.582L315.03,425.554L320.367,424.869L322.518,424.035L324.084,422.96L325.218,422.029L326.73,421.145ZM284.277,425.639L289.902,425.736L295.293,425.981L297.156,424.953L298.479,424.073L301.071,425.101L300.333,426.375L299.604,427.501L294.366,427.158L288.777,427.306L285.645,426.472L285.645,426.375ZM265.215,403.174L266.925,402.878L269.814,402.975L270.552,401.702L270.696,400.775L270.642,398.765L272.064,397.589L274.368,397.195L275.691,398.126L276.276,399.057L277.356,400.187L278.184,401.262L278.868,402.391L279.165,403.517L278.724,404.494L278.04,405.425L275.106,405.768L272.307,406.259L269.031,406.212L270.255,405.231L267.312,405.573L264.522,405.916L262.614,405.18L262.47,404.152ZM194.177,404.736L195.743,404.296L198.92,404.638L202.547,404.833L205.292,405.176L208.028,404.884L209.495,406.301L207.542,406.107L204.509,406.204L201.422,406.107L198.038,406.255L195.491,405.764ZM143.443,409.145L143.983,408.311L146.971,408.751L150.203,409.145L153.191,408.705L151.769,409.585L149.419,410.224L145.945,410.025ZM131.788,408.654L133.606,408.116L136.099,408.705L139.924,409.682L138.448,409.585L135.217,409.339ZM40.716,421.488L42.237,420.557L46.89,420.95L49.383,421.733L51.292,422.617L51.976,423.743L47.178,424.086L43.902,423.206L42.435,422.321L42.336,422.173ZM0,436.784L0,436.784L0,436.784L0.144,436.805L2.349,435.35L6.858,436.133L7.146,436.044L9.792,435.248L10.134,435.278L10.422,435.295L14.04,436.336L17.208,435.295L17.775,435.151L25.119,434.711L27.504,435.295L28.674,435.595L32.445,436.425L39.546,437.063L45.171,437.846L54.82,438.434L62.02,437.749L72.649,438.24L78.67,439.023L85.276,438.286L92.233,437.601L92.773,436.425L82.927,436.327L74.845,435.739L72.739,434.762L66.034,434.22L66.475,433.094L67.402,432.066L68.338,431.135L67.843,430.107L63.685,429.422L61.777,428.537L57.907,427.754L63.982,427.902L69.76,427.509L73.378,428.343L77.833,427.611L81.946,426.68L83.953,425.846L83.071,424.818L79.84,424.132L76.168,423.396L71.029,423.248L66.529,422.905L61.678,422.66L60.058,421.729L56.827,420.946L54.874,420.066L54.091,417.222L55.315,417.468L57.565,418.251L61.678,418.005L65.647,417.663L67.699,418.742L71.668,418.496L74.998,417.959L78.13,417.273L80.965,416.44L84.736,416.194L84.637,415.263L83.764,414.332L84.493,413.452L87.724,413.012L89.191,413.842L93.016,413.355L95.905,412.716L99.478,412.665L102.853,412.424L106.237,411.836L108.928,411.294L111.961,410.757L113.923,410.905L115.633,411.1L119.359,410.757L122.689,411.197L126.118,411.15L129.394,410.808L132.769,411.049L136.495,411.294L139.969,411.197L143.596,411.248L147.313,411.294L150.743,411.197L153.29,410.461L156.323,410.071L159.464,410.609L162.443,410.169L165.143,409.289L166.754,410.071L167.636,410.952L169.256,411.785L171.848,411.049L174.836,411.98L178.211,412.276L181.1,412.961L184.628,412.813L187.814,412.373L191.576,412.471L194.96,412.813L198.389,413.253L199.712,412.179L198.092,411.345L196.868,410.461L193.637,410.266L192.215,409.335L191.675,408.404L190.793,406.542L192.71,406.885L195.986,407.033L199.217,406.885L202.16,407.279L204.707,408.015L205.778,408.895L209.162,409.043L212.393,408.7L215.822,408.21L218.9,407.913L221.447,408.502L224.777,408.307L226.928,406.399L228.944,407.524L231.833,407.964L234.965,407.719L237.017,408.7L240.302,408.798L243.335,409.09L246.323,409.631L248.285,408.7L249.257,407.816L251.76,408.798L255.189,408.552L257.736,409.09L259.446,409.923L262.776,409.678L265.368,409.14L267.915,408.502L270.948,408.159L274.476,407.867L277.662,407.524L280.11,406.987L281.577,406.2L282.162,405.125L281.874,404.092L281.091,403.115L280.209,402.133L279.426,401.156L278.787,400.271L278.643,399.294L278.886,398.312L280.056,397.381L281.037,396.353L281.433,395.376L280.938,394.297L280.65,393.315L281.874,392.189L283.242,391.457L284.862,390.527L286.572,389.74L288.579,389.007L289.56,387.928L290.928,387.243L292.494,386.604L294.897,386.46L296.463,385.673L298.227,385.187L300.279,384.89L302.097,384.256L303.51,383.469L305.472,383.177L306.939,383.816L306.012,384.645L303.465,385.381L302.385,385.919L300.531,385.529L298.47,385.775L296.76,386.363L294.942,386.998L293.718,387.734L293.376,388.711L293.529,389.642L294.699,390.476L292.989,391.064L290.64,391.259L289.263,392.092L287.796,392.875L286.23,393.954L285.834,394.885L286.716,395.913L288.039,396.696L290.1,397.284L292.008,398.067L293.034,399.049L293.574,399.979L294.312,400.961L295.482,401.791L296.22,402.721L296.562,405.023L297.291,405.954L297.489,406.936L298.272,407.913L297.93,409.238L296.562,410.266L295.095,411.1L291.765,411.442L290.64,412.322L289.119,413.156L285.348,414.087L282.018,414.48L278.886,415.018L275.502,415.56L273.495,416.588L269.481,416.685L265.08,416.588L261.111,416.782L256.899,416.782L257.682,417.764L261.498,418.204L264.297,418.89L265.863,419.77L263.073,420.553L258.762,420.307L255.189,420.946L255.036,421.974L254.937,422.956L257.88,423.785L258.42,424.716L261.597,425.647L266.889,426.041L271.389,426.726L274.971,427.509L279.525,428.296L285.735,428.685L291.864,429.371L296.121,430.107L300.774,430.941L303.222,432.117L304.446,433.048L307.479,432.164L311.592,431.431L315.948,430.644L321.141,430.01L325.596,429.324L331.815,429.273L337.935,429.616L342.975,430.204L344.595,429.125L348.069,428.393L354.388,428.343L359.338,427.805L364.036,427.264L369.229,426.921L374.755,426.481L378.625,425.846L376.861,424.962L375.79,424.082L375.79,423.151L370.939,423.248L365.8,423.641L360.904,423.641L360.211,422.711L360.562,420.849L361.687,420.307L365.26,419.723L369.472,419.135L372.505,418.399L375.538,417.663L377.797,416.685L381.217,416.245L384.601,415.902L386.311,415.703L390.181,415.606L393.853,415.263L396.94,414.772L399.973,414.184L402.718,413.596L406.192,412.813L408.397,411.98L410.746,411.248L411.484,410.266L408.838,409.678L409.72,408.65L411.385,407.867L413.977,407.376L416.722,406.788L419.269,406.005L421.222,405.023L422.446,403.851L424.264,403.162L427.243,403.31L428.467,404.143L431.455,404.241L431.554,403.31L432.832,402.332L435.523,402.578L436.162,403.508L439.141,403.652L442.381,403.212L445.513,402.92L448.348,403.064L449.428,404.092L452.174,403.263L454.721,402.819L457.556,402.476L460.346,402.133L462.893,401.545L465.683,401.156L467.843,400.614L469.355,399.734L471.218,400.373L473.81,400.03L475.628,401.202L477.041,402.087L479.885,401.596L481.01,400.614L483.557,399.929L486.842,400.077L487.814,401.008L489.875,400.077L492.566,399.785L495.5,399.688L498.146,399.734L500.936,400.03L503.636,400.174L504.806,401.008L506.426,401.744L509.162,401.304L512.105,401.202L514.94,401.202L517.73,401.156L520.232,400.813L522.878,400.517L525.083,399.831L527.432,399.391L529.979,399.146L531.887,398.46L533.255,397.089L534.677,396.256L537.269,396.649L538.25,397.53L540.401,398.118L543.002,397.923L544.766,398.803L546.62,399.442L549.167,398.854L550.05,397.775L552.3,397.335L554.901,396.501L557.349,396.159L560.283,395.668L562.245,395.13L564.297,394.542L566.259,394.005L568.608,394.297L570.858,393.417L572.478,392.731L574.827,392.778L576.888,392.189L577.374,391.309L579.48,390.624L581.532,390.133L584.034,389.74L586.338,389.545L588.534,389.693L590.892,389.938L592.899,390.624L593.142,391.699L595.347,392.532L596.859,393.218L599.847,393.514L601.512,394.199L603.573,394.885L605.967,395.033L607.974,394.542L610.134,393.514L612.483,394.051L614.931,394.348L617.28,394.639L619.728,394.834L622.221,394.834L624.282,397.432L624.183,398.067L623.886,399.197L621.492,399.831L619.53,400.762L619.872,401.744L622.662,401.693L622.32,402.675L621.051,403.606L619.872,404.634L621.78,405.417L624.669,405.662L627.558,405.222L628.935,404.241L629.763,403.31L631.14,402.527L632.706,401.791L633.336,400.91L634.659,399.688L636.225,399.442L639.069,399.341L641.562,399.049L644.109,398.655L645.333,397.678L646.071,396.747L647.781,395.816L650.23,395.177L652.336,394.69L653.713,393.857L655.126,393.417L656.944,393.023L659.437,393.269L661.687,393.023L664.135,392.731L666.88,392.875L668.689,392.189L669.967,390.527L670.894,391.212L672.073,392.388L674.179,392.875L676.573,393.074L678.976,392.778L681.523,392.972L683.872,393.023L685.438,392.778L687.544,392.926L689.452,393.463L691.702,393.12L694.402,393.12L696.697,392.778L699.298,393.12L700.963,392.287L702.232,391.457L703.951,390.768L707.083,388.91L708.694,389.253L710.602,389.938L712.267,390.819L715.453,392.338L717.901,392.388L720.205,392.388L722.896,392.092L725.587,391.749L727.648,391.064L729.358,390.328L732.148,390.23L734.011,389.693L735.973,390.184L737.242,390.967L739.006,391.749L741.751,391.652L743.461,392.287L746.449,392.926L749.581,393.171L752.174,392.972L754.136,392.189L755.801,391.407L758.051,391.212L760.31,391.555L762.902,391.8L765.251,391.407L767.501,391.407L769.706,391.652L772.01,391.898L774.26,391.457L776.951,391.064L779.498,390.967L782.342,390.967L784.637,390.721L786.896,390.527L787.58,389.299L787.679,388.271L789.245,388.957L789.686,390.082L790.514,391.115L791.549,391.944L793.655,392.388L796.49,392.24L799.775,392.189L802.025,392.041L805.301,392.041L807.659,391.995L810.935,392.092L813.725,392.287L815.489,393.074L815.003,394.005L816.614,394.737L819.305,395.325L822.095,395.964L825.335,396.404L828.71,396.793L831.257,397.187L834.092,397.238L835.712,396.404L837.917,397.089L839.825,397.872L842.03,398.46L845.063,398.706L847.952,398.998L849.176,399.979L852.021,400.568L853.929,401.448L856.719,401.841L859.608,401.791L862.299,401.939L865.287,401.888L868.275,402.087L871.065,402.429L873.657,403.018L876.258,403.508L878.013,404.241L877.725,405.222L876.402,406.102L875.277,407.228L874.395,408.112L873.216,409.14L869.94,409.534L868.473,410.414L865.233,410.952L864.108,411.933L862.398,412.864L860.589,413.647L859.554,414.675L858.924,415.606L858.672,416.732L858.726,417.663L860.148,418.644L860.688,419.575L861.858,420.455L866.511,420.798L867.492,421.877L862.983,422.27L859.167,422.808L854.415,422.905L852.309,424.327L851.868,425.503L850.797,426.434L849.473,427.365L852.804,428.194L854.073,429.227L856.224,430.154L859.266,430.987L862.74,431.774L866.511,432.557L872.235,433.34L873.513,434.563L880.713,435.104L881.19,435.295L883.062,436.035L889.965,435.396L895.689,436.183L900,436.784L900,436.784L900,450L450,450L0,450ZM531.833,137.151L532.004,137.138L532.364,136.533L534.164,136.567L536.441,135.822L534.749,136.884L534.938,137.354L534.668,137.265L534.191,137.455L533.813,137.404L533.687,137.498L533.642,137.248L533.462,137.091L532.976,137.066L532.301,137.282ZM531.833,137.151L532.301,137.282L532.976,137.066L533.462,137.091L533.642,137.248L533.687,137.498L533.813,137.404L534.191,137.455L534.668,137.265L534.938,137.354L535.01,137.557L532.445,138.572L531.221,138.246L530.645,137.244ZM444.577,137.079L445.513,138.682L445.666,140.201L446.53,142.842L447.187,143.371L446.728,144.344L443.461,144.763L442.327,145.689L440.878,145.905L440.77,147.759L437.854,148.749L436.891,149.997L434.848,150.67L432.355,151.051L428.314,152.896L428.332,155.858L427.954,155.858L428.017,157.199L426.469,157.279L425.659,157.846L424.525,157.846L423.625,157.525L421.519,157.791L420.7,159.738L419.926,159.924L418.747,163.076L415.273,165.772L414.445,169.225L413.419,170.346L413.122,171.247L407.497,171.45L407.452,171.446L407.569,170.287L408.523,169.605L409.342,168.302L409.18,167.456L410.044,165.691L411.439,164.1L412.276,163.698L412.942,162.243L412.996,160.91L413.896,159.365L415.561,158.451L417.154,155.9L417.199,155.866L418.45,154.905L420.781,154.63L422.743,152.921L424.003,152.252L426.091,150.166L425.461,147.056L426.415,144.907L426.748,143.586L428.359,141.898L430.861,140.756L432.715,139.723L434.389,137.134L435.172,135.602L437.017,135.61L438.52,136.672L440.896,136.499L443.488,137.053ZM542.165,169.999L532.247,169.999L522.554,169.999L512.501,169.999L512.501,160.796L512.501,151.905L511.754,149.891L512.393,148.347L512.006,147.276L512.915,146.079L516.236,146.036L518.648,146.697L521.123,147.437L522.284,147.826L524.21,147.031L525.236,146.316L527.441,146.108L529.223,146.426L529.898,147.666L530.483,146.849L532.481,147.441L534.434,147.581L535.667,146.95L537.062,150.598L537.305,151.245L536.603,152.252L536.063,154.14L535.388,155.443L534.803,155.879L533.966,155.071L532.841,153.958L531.059,150.374L530.798,150.598L531.833,153.238L533.372,155.752L535.262,159.645L536.18,161.003L536.99,162.416L539.231,165.184L538.736,165.619L538.817,167.244L541.724,169.487ZM512.501,169.999L512.501,174.992L509.621,175L509.594,176.05L499.622,171.264L489.65,166.474L487.13,167.841L485.357,168.772L483.953,167.401L480.002,166.322L478.904,164.756L476.933,163.593L475.763,164.054L474.872,162.657L474.773,161.587L473.297,159.763L474.287,158.718L474.071,157.148L474.395,155.781L474.206,154.639L474.647,152.599L474.512,151.44L473.702,149.231L474.926,148.651L475.142,147.594L474.872,146.561L476.591,145.596L477.365,144.797L478.58,144.077L478.724,142.156L481.658,143.019L482.711,142.804L484.799,143.218L488.111,144.335L489.281,146.561L491.531,147.044L495.05,148.093L497.714,149.333L498.938,148.685L500.135,147.534L499.55,145.622L500.333,144.403L502.133,143.231L503.861,142.893L507.236,143.405L508.091,144.522L509.027,144.53L509.819,144.957L512.303,145.254L512.915,146.079L512.006,147.276L512.393,148.347L511.754,149.891L512.501,151.905L512.501,160.796ZM569.472,204.993L562.407,212.495L559.149,212.605L556.926,214.369L555.324,214.416L554.64,215.203L552.93,215.203L551.922,214.357L549.635,215.402L548.897,216.447L547.232,216.248L546.674,215.96L546.089,216.028L545.306,216.003L542.138,213.878L540.401,213.878L539.546,213.058L539.546,211.653L538.241,211.234L536.765,208.513L535.622,207.933L535.19,206.935L533.921,205.716L532.382,205.538L533.237,204.112L534.56,204.053L534.938,203.287L534.902,201.04L535.64,198.425L536.828,197.723L537.08,196.703L538.151,194.795L539.663,193.555L540.671,191.092L541.076,188.943L543.983,189.468L544.766,187.601L546.278,188.735L547.745,188.147L548.348,188.672L550.068,188.702L552.246,189.704L552.885,190.568L554.001,191.372L555.027,192.836L555.882,193.644L555,194.748L554.154,195.92L554.352,196.61L554.388,197.372L555.783,197.414L556.386,197.236L556.944,197.685L556.395,198.569L557.322,199.944L558.24,201.15L559.194,202.039L567.375,205.009ZM555.882,193.644L556.953,193.86L557.7,193.25L558.294,194.025L558.213,195.061L556.791,195.662L557.862,196.344L556.944,197.685L556.386,197.236L555.783,197.414L554.388,197.372L554.352,196.61L554.154,195.92L555,194.748ZM572.37,196.475L572.352,196.513L572.343,197.545L572.343,200.067L572.343,201.37L571.218,202.906L569.472,204.993L567.375,205.009L559.194,202.039L558.24,201.15L557.322,199.944L556.395,198.569L556.944,197.685L557.862,196.344L558.681,196.805L559.167,197.841L560.292,198.887L561.534,198.895L563.892,198.256L566.61,197.96L568.815,197.181L570.057,197.016L570.948,196.559ZM534.758,227.377L529.664,227.567L526.928,227.537L526.046,227.838L524.552,228.608L523.949,228.354L523.967,226.467L524.552,225.515L524.687,223.505L525.218,222.345L526.172,221.042L527.135,220.378L527.936,219.489L526.937,219.151L527.081,216.227L528.116,215.546L529.7,216.104L531.716,215.52L533.471,215.524L535.01,214.374L536.198,216.113L536.486,217.365L537.593,220.234L536.684,222.058L535.451,223.712L534.731,224.724ZM526.046,227.838L527.036,229.247L526.892,230.719L526.172,231.033L524.849,230.872L524.084,232.293L522.563,232.099L522.797,230.732L523.139,230.537L523.229,229.052L523.949,228.354L524.552,228.608ZM496.4,118.376L494.186,117.428L493.241,116.383L492.287,115.833L491.144,114.898L490.595,114.123L489.371,112.951L489.902,111.914L490.793,112.49L491.333,111.969L492.503,111.914L494.654,112.329L496.382,112.295L497.516,112.85L498.416,112.841L497.795,113.941L499.001,114.902L498.632,116.078L498.047,116.192L497.579,116.417L496.769,117.001ZM505.949,119.201L507.2,120.001L507.38,121.655L506.903,121.74L506.489,122.176L505.139,122.125L504.185,122.671L502.547,122.895L501.512,122.286L501.161,121.211L501.476,120.36L501.791,120.382L501.908,119.87L503.384,119.484L503.942,119.387L504.797,119.239ZM497.075,110.226L498.992,109.57L500.549,109.68L501.908,110.662L502.187,111.457L503.708,112.046L503.906,113.078L505.364,113.806L506.147,113.243L506.768,113.556L506.183,113.975L506.642,114.411L506.03,114.978L506.246,115.892L507.461,116.971L506.516,117.754L506.093,118.549L506.363,118.846L505.949,119.201L504.797,119.239L503.942,119.387L503.861,119.201L504.158,118.901L504.437,118.291L504.086,118.308L503.6,117.843L503.186,117.724L502.862,117.326L502.394,117.174L502.034,116.819L501.584,116.958L501.242,117.788L500.648,117.97L500.846,117.754L499.892,117.233L499.073,116.967L498.713,116.62L498.047,116.192L498.632,116.078L499.001,114.902L497.795,113.941L498.416,112.841L497.516,112.85L498.479,111.91L497.678,111.195ZM500.18,118.528L499.505,118.748L499.343,118.279L498.263,119.51L498.425,120.305L497.903,120.111L497.201,119.298L496.121,118.799L496.4,118.376L496.769,117.001L497.579,116.417L498.047,116.192L498.713,116.62L499.073,116.967L499.892,117.233L500.846,117.754L500.648,117.97ZM501.476,120.36L501.305,119.455L500.711,119.201L500.18,118.528L500.648,117.97L501.242,117.788L501.584,116.958L502.034,116.819L502.394,117.174L502.862,117.326L503.186,117.724L503.6,117.843L504.086,118.308L504.437,118.291L504.158,118.901L503.861,119.201L503.942,119.387L503.384,119.484L501.908,119.87L501.791,120.382ZM295.797,198.1L297.237,197.774L297.759,197.863L297.66,199.724L295.572,199.999L295.122,199.775L295.851,199.085ZM527.081,216.227L524.885,214.564L524.291,213.498L522.896,214.027L521.744,213.862L521.069,214.28L519.953,213.98L518.432,211.915L518.036,211.124L516.164,210.134L515.534,208.632L514.49,207.553L512.807,206.249L512.789,205.437L511.421,204.426L509.72,203.452L510.485,203.177L511.34,202.708L511.988,200.473L512.672,199.314L514.472,198.971L514.904,199.661L516.191,201.117L516.884,201.332L517.784,200.905L519.584,200.99L519.926,201.506L522.419,201.506L522.5,200.99L523.787,200.516L524.048,199.788L524.993,199.272L527.09,200.732L528.386,200.473L529.628,198.671L530.996,197.3L530.789,195.798L530.186,195.066L531.689,194.939L531.86,194.38L533.021,194.554L532.715,196.399L533.021,198.201L534.308,199.187L534.605,200.046L534.56,201.29L534.911,201.341L534.938,203.287L534.56,204.053L533.237,204.112L532.382,205.538L533.921,205.716L535.19,206.935L535.622,207.933L536.765,208.513L538.241,211.234L536.549,212.884L535.01,214.374L533.471,215.524L531.716,215.52L529.7,216.104L528.116,215.546Z";

// src/ActivitySparkline.svelte
var root = from_svg(`<polyline class="wh-spark-line"></polyline>`);
var root_1 = from_svg(`<circle cx="3" r="2" class="wh-spark-zero"></circle>`);
var root_2 = from_html(`<span class="wh-spark"><svg role="img" aria-hidden="true"><line x1="2" class="wh-spark-base"></line><!></svg> <span class="wh-spark-caption"> </span></span>`);
function ActivitySparkline($$anchor, $$props) {
  push($$props, false);
  const counts = mutable_source();
  const peak = mutable_source();
  const points = mutable_source();
  const total = mutable_source();
  let series = prop($$props, "series", 24, () => ({
    measure: "event_count",
    aggregation: "week",
    window: "latest_12_weeks",
    bins: []
  }));
  let width = prop($$props, "width", 8, 108);
  let height = prop($$props, "height", 8, 26);
  legacy_pre_effect(() => deep_read_state(series()), () => {
    set(counts, (series()?.bins || []).map((bin) => bin.count));
  });
  legacy_pre_effect(() => get(counts), () => {
    set(peak, Math.max(1, ...get(counts)));
  });
  legacy_pre_effect(
    () => (get(counts), deep_read_state(width()), deep_read_state(height()), get(peak)),
    () => {
      set(points, get(counts).map((count, index2) => `${2 + index2 * (width() - 4) / Math.max(1, get(counts).length - 1)},${height() - 3 - count / get(peak) * (height() - 7)}`).join(" "));
    }
  );
  legacy_pre_effect(() => get(counts), () => {
    set(total, get(counts).reduce((sum, count) => sum + count, 0));
  });
  legacy_pre_effect_reset();
  init();
  var span = root_2();
  var svg = child(span);
  var line = child(svg);
  var node = sibling(line);
  {
    var consequent = ($$anchor2) => {
      var polyline = root();
      template_effect(() => set_attribute2(polyline, "points", get(points)));
      append($$anchor2, polyline);
    };
    var alternate = ($$anchor2) => {
      var circle = root_1();
      template_effect(() => set_attribute2(circle, "cy", height() - 3));
      append($$anchor2, circle);
    };
    if_block(node, ($$render) => {
      if (get(counts), untrack(() => get(counts).length > 1)) $$render(consequent);
      else $$render(alternate, -1);
    });
  }
  reset(svg);
  var span_1 = sibling(svg, 2);
  var text2 = only_child(span_1);
  reset(span);
  template_effect(
    ($0) => {
      set_attribute2(span, "title", $0);
      set_attribute2(span, "aria-label", `\u622A\u81F3\u6700\u65B0 Event \u6240\u5728\u5468\u7684 12 \u5468 Event \u6D3B\u52A8\uFF1A${get(total)} \u6761\uFF1B\u6309\u5468\u8BA1\u6570`);
      set_attribute2(svg, "viewBox", `0 0 ${width()} ${height()}`);
      set_attribute2(svg, "width", width());
      set_attribute2(svg, "height", height());
      set_attribute2(line, "y1", height() - 3);
      set_attribute2(line, "x2", width() - 2);
      set_attribute2(line, "y2", height() - 3);
      set_text(text2, `${get(total) ?? ""} Events / 12 \u5468`);
    },
    [
      () => (get(counts), untrack(() => `\u622A\u81F3\u6700\u65B0 Event \u6240\u5728\u5468\u7684 12 \u5468\uFF0C\u6BCF\u5468\u53D1\u751F\u7684 Event\uFF1A${get(counts).join("\u3001") || "\u65E0\u65E5\u671F\u8BB0\u5F55"}`))
    ]
  );
  append($$anchor, span);
  pop();
}

// src/ThreadProjection.svelte
var root2 = from_html(`<small title="Claim \u4FEE\u6B63">\u21BA</small>`);
var root_12 = from_html(`<small title="Claim \u4E89\u8BAE">\u21C4</small>`);
var root_22 = from_html(`<button class="wh-mini-event"><span></span><time> </time><span> </span><!><!></button>`);
var root_3 = from_html(`<p class="wh-muted">\u5C1A\u65E0 Event\u3002</p>`);
var root_4 = from_html(`<!> <div class="wh-mini-timeline"></div>`, 1);
var root_5 = from_svg(`<line x1="140" y1="90" class="wh-mini-edge"><title>\u6D89\u53CA Entity</title></line>`);
var root_6 = from_svg(`<g role="button" tabindex="0"><circle r="12" class="wh-mini-entity"></circle><title> </title></g>`);
var root_7 = from_html(`<button class="wh-mini-link"> </button>`);
var root_8 = from_html(`<p class="wh-muted">\u6B64 Thread \u6682\u65E0\u5173\u8054 Entity\u3002</p>`);
var root_9 = from_html(`<svg class="wh-mini-graph" viewBox="0 0 280 180" role="img"><!><rect x="98" y="74" width="84" height="32" rx="12" class="wh-mini-thread"></rect><text x="140" y="94" text-anchor="middle">Thread</text><!></svg> <div class="wh-mini-legend">\u25A2 Thread\u3000\u25CF Entity \xB7 \u5173\u7CFB\uFF1A\u6D89\u53CA</div> <!>`, 1);
var root_10 = from_svg(`<g role="button" tabindex="0"><circle></circle><title> </title></g>`);
var root_11 = from_html(`<svg class="wh-mini-map" viewBox="0 0 900 450" role="img"><path class="wh-world-shape"></path><!></svg> <div class="wh-mini-legend">\u25CF \u7CBE\u786E / \u57CE\u5E02\u3000\u25CC \u533A\u57DF / \u8FD1\u4F3C</div> <!>`, 1);
var root_122 = from_html(`<p class="wh-muted">\u6B64 Thread \u6CA1\u6709\u6709\u5750\u6807\u7684 Event \u5730\u70B9\u3002</p>`);
var root_13 = from_html(`<div class="wh-projection"><!></div>`);
function ThreadProjection($$anchor, $$props) {
  push($$props, false);
  const scoped = mutable_source();
  const scopedEvents = mutable_source();
  const events = mutable_source();
  const series = mutable_source();
  const entityIds = mutable_source();
  const entities = mutable_source();
  const locationIds = mutable_source();
  const locations = mutable_source();
  let thread = prop($$props, "thread", 8);
  let repository = prop($$props, "repository", 8);
  let scope = prop($$props, "scope", 24, () => ({
    search: "",
    from: "",
    to: "",
    threadId: "",
    entityId: "",
    locationId: "",
    status: "",
    priority: "",
    claimState: ""
  }));
  let projection = prop($$props, "projection", 8, "Time");
  let openEvent = prop($$props, "openEvent", 8, () => {
  });
  let openEntity = prop($$props, "openEntity", 8, () => {
  });
  let openLocation = prop($$props, "openLocation", 8, () => {
  });
  function scopedSeries(items) {
    const dated = items.map((event2) => event2.occurred_at || event2.reported_at || event2.first_observed_at).filter(Boolean).map((value) => /* @__PURE__ */ new Date(value.slice(0, 10) + "T00:00:00Z")).filter((date) => Number.isFinite(date.getTime()));
    if (!dated.length) return {
      measure: "event_count",
      aggregation: "week",
      window: "latest_12_weeks",
      bins: []
    };
    const end = new Date(dated.reduce((latest, date) => Math.max(latest, date.getTime()), 0));
    end.setUTCDate(end.getUTCDate() - (end.getUTCDay() + 6) % 7);
    const start = new Date(end);
    start.setUTCDate(start.getUTCDate() - 77);
    const bins = Array.from({ length: 12 }, (_, i) => {
      const day = new Date(start);
      day.setUTCDate(day.getUTCDate() + i * 7);
      return { start: day.toISOString().slice(0, 10), count: 0 };
    });
    for (const date of dated) {
      const week = new Date(date);
      week.setUTCDate(week.getUTCDate() - (week.getUTCDay() + 6) % 7);
      const index2 = Math.floor((week.getTime() - start.getTime()) / 6048e5);
      if (index2 >= 0 && index2 < 12) bins[index2].count++;
    }
    return {
      measure: "event_count",
      aggregation: "week",
      window: "latest_12_weeks",
      bins
    };
  }
  legacy_pre_effect(() => deep_read_state(scope()), () => {
    set(scoped, Object.values(scope()).some(Boolean));
  });
  legacy_pre_effect(
    () => (deep_read_state(thread()), get(scoped), deep_read_state(repository()), deep_read_state(scope())),
    () => {
      set(scopedEvents, (thread()?.event_summaries || []).filter((event2) => !get(scoped) || repository().matchesEvent(event2, scope())));
    }
  );
  legacy_pre_effect(() => get(scopedEvents), () => {
    set(events, get(scopedEvents).slice(0, 6));
  });
  legacy_pre_effect(
    () => (get(scoped), get(scopedEvents), deep_read_state(thread())),
    () => {
      set(series, get(scoped) ? scopedSeries(get(scopedEvents)) : thread().activity_series);
    }
  );
  legacy_pre_effect(
    () => (get(scoped), get(scopedEvents), deep_read_state(thread())),
    () => {
      set(entityIds, get(scoped) ? [
        ...new Set(get(scopedEvents).flatMap((event2) => event2.entity_ids))
      ] : thread()?.top_entity_ids || []);
    }
  );
  legacy_pre_effect(() => (get(entityIds), deep_read_state(repository())), () => {
    set(entities, get(entityIds).slice(0, 5).map((id) => repository().entityById.get(id)).filter(Boolean));
  });
  legacy_pre_effect(
    () => (get(scoped), get(scopedEvents), deep_read_state(thread())),
    () => {
      set(locationIds, get(scoped) ? [
        ...new Set(get(scopedEvents).flatMap((event2) => event2.location_ids))
      ] : thread()?.location_ids || []);
    }
  );
  legacy_pre_effect(() => (get(locationIds), deep_read_state(repository())), () => {
    set(locations, get(locationIds).slice(0, 18).map((id) => repository().locationById.get(id)).filter(Boolean));
  });
  legacy_pre_effect_reset();
  init();
  var div = root_13();
  var node = child(div);
  {
    var consequent_2 = ($$anchor2) => {
      var fragment = root_4();
      var node_1 = first_child(fragment);
      ActivitySparkline(node_1, {
        get series() {
          return get(series);
        },
        width: 220,
        height: 46
      });
      var div_1 = sibling(node_1, 2);
      each(
        div_1,
        5,
        () => get(events),
        index,
        ($$anchor3, event2) => {
          var button = root_22();
          var span = child(button);
          let classes;
          var time = sibling(span);
          var text2 = only_child(time, true);
          var span_1 = sibling(time);
          var text_1 = only_child(span_1, true);
          var node_2 = sibling(span_1);
          {
            var consequent = ($$anchor4) => {
              var small = root2();
              append($$anchor4, small);
            };
            if_block(node_2, ($$render) => {
              if (get(event2), untrack(() => get(event2).has_corrected_claim)) $$render(consequent);
            });
          }
          var node_3 = sibling(node_2);
          {
            var consequent_1 = ($$anchor4) => {
              var small_1 = root_12();
              append($$anchor4, small_1);
            };
            if_block(node_3, ($$render) => {
              if (get(event2), untrack(() => get(event2).has_contested_claim)) $$render(consequent_1);
            });
          }
          reset(button);
          template_effect(
            ($0) => {
              set_attribute2(button, "title", (get(event2), untrack(() => get(event2).title)));
              classes = set_class(span, 1, "wh-mini-dot", null, classes, {
                approximate: get(event2).time_precision !== "day",
                corrected: get(event2).has_corrected_claim,
                contested: get(event2).has_contested_claim
              });
              set_text(text2, $0);
              set_text(text_1, (get(event2), untrack(() => get(event2).title)));
            },
            [
              () => (get(event2), untrack(() => (get(event2).occurred_at || get(event2).reported_at || get(event2).first_observed_at || "\u672A\u77E5").slice(0, 10)))
            ]
          );
          event("click", button, () => openEvent()(get(event2)));
          append($$anchor3, button);
        },
        ($$anchor3) => {
          var p = root_3();
          append($$anchor3, p);
        }
      );
      reset(div_1);
      append($$anchor2, fragment);
    };
    var consequent_3 = ($$anchor2) => {
      var fragment_1 = root_9();
      var svg = first_child(fragment_1);
      var node_4 = child(svg);
      each(node_4, 1, () => get(entities), index, ($$anchor3, entity, i) => {
        var line = root_5();
        template_effect(
          ($0, $1) => {
            set_attribute2(line, "x2", $0);
            set_attribute2(line, "y2", $1);
          },
          [
            () => (i, get(entities), untrack(() => 140 + 95 * Math.cos(2 * Math.PI * i / get(entities).length - Math.PI / 2))),
            () => (i, get(entities), untrack(() => 90 + 62 * Math.sin(2 * Math.PI * i / get(entities).length - Math.PI / 2)))
          ]
        );
        append($$anchor3, line);
      });
      var node_5 = sibling(node_4, 3);
      each(node_5, 1, () => get(entities), index, ($$anchor3, entity, i) => {
        var g = root_6();
        var circle = child(g);
        var title = sibling(circle);
        var text_2 = only_child(title);
        reset(g);
        template_effect(
          ($0, $1) => {
            set_attribute2(circle, "cx", $0);
            set_attribute2(circle, "cy", $1);
            set_text(text_2, `${(get(entity), untrack(() => get(entity).name)) ?? ""} \xB7 \u6D89\u53CA Entity`);
          },
          [
            () => (i, get(entities), untrack(() => 140 + 95 * Math.cos(2 * Math.PI * i / get(entities).length - Math.PI / 2))),
            () => (i, get(entities), untrack(() => 90 + 62 * Math.sin(2 * Math.PI * i / get(entities).length - Math.PI / 2)))
          ]
        );
        event("click", g, () => openEntity()(get(entity).entity_id));
        event("keydown", g, (event2) => event2.key === "Enter" && openEntity()(get(entity).entity_id));
        append($$anchor3, g);
      });
      reset(svg);
      var node_6 = sibling(svg, 4);
      each(
        node_6,
        1,
        () => get(entities),
        index,
        ($$anchor3, entity) => {
          var button_1 = root_7();
          var text_3 = only_child(button_1, true);
          template_effect(() => set_text(text_3, (get(entity), untrack(() => get(entity).name))));
          event("click", button_1, () => openEntity()(get(entity).entity_id));
          append($$anchor3, button_1);
        },
        ($$anchor3) => {
          var p_1 = root_8();
          append($$anchor3, p_1);
        }
      );
      template_effect(() => set_attribute2(svg, "aria-label", (deep_read_state(thread()), get(entities), untrack(() => `Thread ${thread().title} \u4E0E ${get(entities).length} \u4E2A\u5173\u8054 Entity`))));
      append($$anchor2, fragment_1);
    };
    var alternate_1 = ($$anchor2) => {
      var fragment_2 = comment();
      var node_7 = first_child(fragment_2);
      {
        var consequent_4 = ($$anchor3) => {
          var fragment_3 = root_11();
          var svg_1 = first_child(fragment_3);
          var path = child(svg_1);
          var node_8 = sibling(path);
          each(node_8, 1, () => get(locations), index, ($$anchor4, location) => {
            var g_1 = root_10();
            var circle_1 = child(g_1);
            let classes_1;
            var title_1 = sibling(circle_1);
            var text_4 = only_child(title_1);
            reset(g_1);
            template_effect(() => {
              set_attribute2(circle_1, "cx", (get(location), untrack(() => (get(location).lon + 180) * 2.5)));
              set_attribute2(circle_1, "cy", (get(location), untrack(() => (90 - get(location).lat) * 2.5)));
              set_attribute2(circle_1, "r", (get(location), untrack(() => get(location).geo_precision === "exact" || get(location).geo_precision === "city" ? 7 : 13)));
              classes_1 = set_class(circle_1, 0, "wh-mini-map-dot", null, classes_1, {
                approximate: get(location).geo_precision !== "exact" && get(location).geo_precision !== "city"
              });
              set_text(text_4, `${(get(location), untrack(() => get(location).name)) ?? ""} \xB7 ${(get(location), untrack(() => get(location).geo_precision)) ?? ""}`);
            });
            event("click", g_1, () => openLocation()(get(location).location_id));
            event("keydown", g_1, (event2) => event2.key === "Enter" && openLocation()(get(location).location_id));
            append($$anchor4, g_1);
          });
          reset(svg_1);
          var node_9 = sibling(svg_1, 4);
          each(node_9, 1, () => get(locations), index, ($$anchor4, location) => {
            var button_2 = root_7();
            var text_5 = only_child(button_2);
            template_effect(() => set_text(text_5, `${(get(location), untrack(() => get(location).name)) ?? ""} \xB7 ${(get(location), untrack(() => get(location).geo_precision)) ?? ""}`));
            event("click", button_2, () => openLocation()(get(location).location_id));
            append($$anchor4, button_2);
          });
          template_effect(() => {
            set_attribute2(svg_1, "aria-label", (deep_read_state(thread()), get(locations), untrack(() => `Thread ${thread().title} \u7684 ${get(locations).length} \u4E2A\u5730\u70B9`)));
            set_attribute2(path, "d", world_path_default);
          });
          append($$anchor3, fragment_3);
        };
        var alternate = ($$anchor3) => {
          var p_2 = root_122();
          append($$anchor3, p_2);
        };
        if_block(node_7, ($$render) => {
          if (get(locations), untrack(() => get(locations).length)) $$render(consequent_4);
          else $$render(alternate, -1);
        });
      }
      append($$anchor2, fragment_2);
    };
    if_block(node, ($$render) => {
      if (projection() === "Time") $$render(consequent_2);
      else if (projection() === "Graph") $$render(consequent_3, 1);
      else $$render(alternate_1, -1);
    });
  }
  reset(div);
  template_effect(() => set_attribute2(div, "data-projection", projection()));
  append($$anchor, div);
  pop();
}

// src/EntityProjection.svelte
var root3 = from_svg(`<line x1="140" y1="90" class="wh-mini-edge"><title> </title></line>`);
var root_14 = from_svg(`<g role="button" tabindex="0"><circle r="10"></circle><title> </title></g>`);
var root_23 = from_html(`<button class="wh-mini-link"> </button>`);
var root_32 = from_html(`<p class="wh-muted">\u6CA1\u6709\u53EF\u89C1\u5173\u7CFB\u3002</p>`);
var root_42 = from_html(`<svg class="wh-mini-graph" viewBox="0 0 280 180" role="img"><!><circle cx="140" cy="90" r="16" class="wh-mini-entity"></circle><text x="140" y="94" text-anchor="middle">E</text><!></svg> <div class="wh-mini-legend">\u25CF Entity\u3000\u25EF Thread \xB7 \u5173\u7CFB\u89C1\u8282\u70B9\u63D0\u793A</div> <!>`, 1);
var root_52 = from_svg(`<g role="button" tabindex="0"><circle></circle><title> </title></g>`);
var root_62 = from_html(`<svg class="wh-mini-map" viewBox="0 0 900 450" role="img"><path class="wh-world-shape"></path><!></svg><div class="wh-mini-legend">\u25CF \u7CBE\u786E / \u57CE\u5E02\u3000\u25CC \u533A\u57DF / \u8FD1\u4F3C \xB7 Event \u53D1\u751F\u5730</div><!>`, 1);
var root_72 = from_html(`<p class="wh-muted">\u6CA1\u6709\u6709\u5750\u6807\u7684\u76F8\u5173 Event \u5730\u70B9\u3002</p>`);
var root_82 = from_html(`<div class="wh-projection"><!></div>`);
function EntityProjection($$anchor, $$props) {
  push($$props, false);
  const scoped = mutable_source();
  const visibleThreads = mutable_source();
  const threads = mutable_source();
  const related = mutable_source();
  const neighbors = mutable_source();
  const scopedEvents = mutable_source();
  const locationIds = mutable_source();
  const locations = mutable_source();
  let entity = prop($$props, "entity", 8);
  let repository = prop($$props, "repository", 8);
  let scope = prop($$props, "scope", 24, () => ({
    search: "",
    from: "",
    to: "",
    threadId: "",
    entityId: "",
    locationId: "",
    status: "",
    priority: "",
    claimState: ""
  }));
  let projection = prop($$props, "projection", 8, "Graph");
  let openThread = prop($$props, "openThread", 8, () => {
  });
  let openEntity = prop($$props, "openEntity", 8, () => {
  });
  let openLocation = prop($$props, "openLocation", 8, () => {
  });
  legacy_pre_effect(() => deep_read_state(scope()), () => {
    set(scoped, Object.values(scope()).some(Boolean));
  });
  legacy_pre_effect(
    () => (get(scoped), deep_read_state(repository()), deep_read_state(scope())),
    () => {
      set(visibleThreads, get(scoped) ? new Set(repository().filteredThreads(scope()).map((thread) => thread.thread_id)) : null);
    }
  );
  legacy_pre_effect(
    () => (deep_read_state(entity()), get(visibleThreads), deep_read_state(repository())),
    () => {
      set(threads, (entity()?.thread_ids || []).filter((id) => !get(visibleThreads) || get(visibleThreads).has(id)).slice(0, 5).map((id) => repository().threadById.get(id)).filter(Boolean));
    }
  );
  legacy_pre_effect(() => (deep_read_state(entity()), deep_read_state(repository())), () => {
    set(related, (entity()?.related_entity_ids || []).slice(0, 4).map((id) => repository().entityById.get(id)).filter(Boolean));
  });
  legacy_pre_effect(() => (get(threads), get(related)), () => {
    set(neighbors, [
      ...get(threads).map((thread) => ({ id: thread.thread_id, label: thread.title, type: "thread" })),
      ...get(related).map((item) => ({ id: item.entity_id, label: item.name, type: "entity" }))
    ]);
  });
  legacy_pre_effect(
    () => (get(scoped), deep_read_state(entity()), deep_read_state(repository()), deep_read_state(scope())),
    () => {
      set(scopedEvents, get(scoped) ? (entity()?.event_ids || []).map((id) => repository().eventById.get(id)).filter((event2) => event2 && repository().matchesEvent(event2, scope())) : []);
    }
  );
  legacy_pre_effect(
    () => (get(scoped), get(scopedEvents), deep_read_state(entity())),
    () => {
      set(locationIds, get(scoped) ? [
        ...new Set(get(scopedEvents).flatMap((event2) => event2.location_ids))
      ] : entity()?.location_ids || []);
    }
  );
  legacy_pre_effect(() => (get(locationIds), deep_read_state(repository())), () => {
    set(locations, get(locationIds).slice(0, 18).map((id) => repository().locationById.get(id)).filter(Boolean));
  });
  legacy_pre_effect_reset();
  init();
  var div = root_82();
  var node = child(div);
  {
    var consequent = ($$anchor2) => {
      var fragment = root_42();
      var svg = first_child(fragment);
      var node_1 = child(svg);
      each(node_1, 1, () => get(neighbors), index, ($$anchor3, neighbor, i) => {
        var line = root3();
        var title = child(line);
        var text2 = only_child(title, true);
        reset(line);
        template_effect(
          ($0, $1) => {
            set_attribute2(line, "x2", $0);
            set_attribute2(line, "y2", $1);
            set_text(text2, (get(neighbor), untrack(() => get(neighbor).type === "thread" ? "\u53C2\u4E0E Thread" : "\u76F8\u5173 Entity")));
          },
          [
            () => (i, get(neighbors), untrack(() => 140 + 96 * Math.cos(2 * Math.PI * i / get(neighbors).length - Math.PI / 2))),
            () => (i, get(neighbors), untrack(() => 90 + 65 * Math.sin(2 * Math.PI * i / get(neighbors).length - Math.PI / 2)))
          ]
        );
        append($$anchor3, line);
      });
      var node_2 = sibling(node_1, 3);
      each(node_2, 1, () => get(neighbors), index, ($$anchor3, neighbor, i) => {
        var g = root_14();
        var circle = child(g);
        let classes;
        var title_1 = sibling(circle);
        var text_1 = only_child(title_1);
        reset(g);
        template_effect(
          ($0, $1) => {
            set_attribute2(circle, "cx", $0);
            set_attribute2(circle, "cy", $1);
            classes = set_class(circle, 0, "", null, classes, {
              "wh-mini-entity": get(neighbor).type === "entity",
              "wh-mini-thread-node": get(neighbor).type === "thread"
            });
            set_text(text_1, `${(get(neighbor), untrack(() => get(neighbor).label)) ?? ""} \xB7 ${(get(neighbor), untrack(() => get(neighbor).type)) ?? ""}`);
          },
          [
            () => (i, get(neighbors), untrack(() => 140 + 96 * Math.cos(2 * Math.PI * i / get(neighbors).length - Math.PI / 2))),
            () => (i, get(neighbors), untrack(() => 90 + 65 * Math.sin(2 * Math.PI * i / get(neighbors).length - Math.PI / 2)))
          ]
        );
        event("click", g, () => get(neighbor).type === "thread" ? openThread()(get(neighbor).id) : openEntity()(get(neighbor).id));
        event("keydown", g, (event2) => event2.key === "Enter" && (get(neighbor).type === "thread" ? openThread()(get(neighbor).id) : openEntity()(get(neighbor).id)));
        append($$anchor3, g);
      });
      reset(svg);
      var node_3 = sibling(svg, 4);
      each(
        node_3,
        1,
        () => get(neighbors),
        index,
        ($$anchor3, neighbor) => {
          var button = root_23();
          var text_2 = only_child(button, true);
          template_effect(() => set_text(text_2, (get(neighbor), untrack(() => get(neighbor).label))));
          event("click", button, () => get(neighbor).type === "thread" ? openThread()(get(neighbor).id) : openEntity()(get(neighbor).id));
          append($$anchor3, button);
        },
        ($$anchor3) => {
          var p = root_32();
          append($$anchor3, p);
        }
      );
      template_effect(() => set_attribute2(svg, "aria-label", (deep_read_state(entity()), get(threads), get(related), untrack(() => `${entity().name} \u4E0E ${get(threads).length} \u4E2A Thread\u3001${get(related).length} \u4E2A Entity \u7684\u5173\u7CFB`))));
      append($$anchor2, fragment);
    };
    var alternate_1 = ($$anchor2) => {
      var fragment_1 = comment();
      var node_4 = first_child(fragment_1);
      {
        var consequent_1 = ($$anchor3) => {
          var fragment_2 = root_62();
          var svg_1 = first_child(fragment_2);
          var path = child(svg_1);
          var node_5 = sibling(path);
          each(node_5, 1, () => get(locations), index, ($$anchor4, location) => {
            var g_1 = root_52();
            var circle_1 = child(g_1);
            let classes_1;
            var title_2 = sibling(circle_1);
            var text_3 = only_child(title_2);
            reset(g_1);
            template_effect(() => {
              set_attribute2(circle_1, "cx", (get(location), untrack(() => (get(location).lon + 180) * 2.5)));
              set_attribute2(circle_1, "cy", (get(location), untrack(() => (90 - get(location).lat) * 2.5)));
              set_attribute2(circle_1, "r", (get(location), untrack(() => get(location).geo_precision === "exact" || get(location).geo_precision === "city" ? 7 : 13)));
              classes_1 = set_class(circle_1, 0, "wh-mini-map-dot", null, classes_1, {
                approximate: get(location).geo_precision !== "exact" && get(location).geo_precision !== "city"
              });
              set_text(text_3, `${(get(location), untrack(() => get(location).name)) ?? ""} \xB7 Event \u5730\u70B9 \xB7 ${(get(location), untrack(() => get(location).geo_precision)) ?? ""}`);
            });
            event("click", g_1, () => openLocation()(get(location).location_id));
            event("keydown", g_1, (event2) => event2.key === "Enter" && openLocation()(get(location).location_id));
            append($$anchor4, g_1);
          });
          reset(svg_1);
          var node_6 = sibling(svg_1, 2);
          each(node_6, 1, () => get(locations), index, ($$anchor4, location) => {
            var button_1 = root_23();
            var text_4 = only_child(button_1);
            template_effect(() => set_text(text_4, `${(get(location), untrack(() => get(location).name)) ?? ""} \xB7 ${(get(location), untrack(() => get(location).geo_precision)) ?? ""}`));
            event("click", button_1, () => openLocation()(get(location).location_id));
            append($$anchor4, button_1);
          });
          template_effect(() => {
            set_attribute2(svg_1, "aria-label", (deep_read_state(entity()), untrack(() => `${entity().name} \u5173\u8054 Event \u7684\u5730\u70B9`)));
            set_attribute2(path, "d", world_path_default);
          });
          append($$anchor3, fragment_2);
        };
        var alternate = ($$anchor3) => {
          var p_1 = root_72();
          append($$anchor3, p_1);
        };
        if_block(node_4, ($$render) => {
          if (get(locations), untrack(() => get(locations).length)) $$render(consequent_1);
          else $$render(alternate, -1);
        });
      }
      append($$anchor2, fragment_1);
    };
    if_block(node, ($$render) => {
      if (projection() === "Graph") $$render(consequent);
      else $$render(alternate_1, -1);
    });
  }
  reset(div);
  template_effect(() => set_attribute2(div, "data-projection", projection()));
  append($$anchor, div);
  pop();
}

// src/ContextCharts.svelte
var root4 = from_html(`<button><span class="wh-chart-track"><span class="wh-chart-covered"></span></span></button>`);
var root_15 = from_html(`<button><span class="wh-chart-track wh-claim-track"><span class="wh-chart-uncertain"></span><span class="wh-chart-contested"></span></span></button>`);
var root_24 = from_html(`<div class="wh-context-charts"><div><h4>Source coverage</h4><div class="wh-chart-bars" aria-label="\u6BCF\u5468 Event \u6765\u6E90\u8986\u76D6\u7387"></div><small>\u6D45\u8272\uFF1A\u6709 Source \u7684 Event\uFF1B\u8F68\u9053\uFF1A\u5168\u90E8 Event\u3002\u6309\u53D1\u751F\u65E5\u671F\u5206\u5468\u3002</small></div> <div><h4>Claim states</h4><div class="wh-chart-bars" aria-label="\u6BCF\u5468 Event \u5173\u8054 Claim \u72B6\u6001"></div><small>\u6DF1\u8272\uFF1A\u4E89\u8BAE\u3001\u4FEE\u6B63\u3001\u53D6\u4EE3\u6216\u64A4\u56DE\uFF1B\u4E2D\u95F4\u8272\uFF1A\u4E0D\u786E\u5B9A\uFF1B\u5176\u4F59\u4E3A\u5176\u4ED6\u72B6\u6001\u3002\u6309 Event \u53D1\u751F\u65E5\u671F\u5206\u5468\uFF0C\u8BA1 Event\u2013Claim \u5173\u8054\u3002</small></div></div>`);
function ContextCharts($$anchor, $$props) {
  push($$props, false);
  const weeks = mutable_source();
  const maxEvents = mutable_source();
  const maxClaims = mutable_source();
  let series = prop($$props, "series", 8);
  let events = prop($$props, "events", 24, () => []);
  let openWeek = prop($$props, "openWeek", 8, () => {
  });
  function weekStart(value) {
    if (!value) return "";
    const date = /* @__PURE__ */ new Date(value.slice(0, 10) + "T00:00:00Z");
    if (Number.isNaN(date.getTime())) return "";
    date.setUTCDate(date.getUTCDate() - (date.getUTCDay() + 6) % 7);
    return date.toISOString().slice(0, 10);
  }
  function summaries(bins, items) {
    const byWeek = new Map((bins || []).map((bin) => [
      bin.start,
      { start: bin.start, events: 0, covered: 0, claimStates: {} }
    ]));
    for (const event2 of items) {
      const week = byWeek.get(weekStart(event2.occurred_at));
      if (!week) continue;
      week.events++;
      if (event2.source_count > 0) week.covered++;
      for (const [state2, count] of Object.entries(event2.claim_state_summary || {})) week.claimStates[state2] = (week.claimStates[state2] || 0) + count;
    }
    return [...byWeek.values()].map((week) => ({
      ...week,
      claims: Object.values(week.claimStates).reduce((sum, count) => sum + count, 0)
    }));
  }
  legacy_pre_effect(() => (deep_read_state(series()), deep_read_state(events())), () => {
    set(weeks, summaries(series()?.bins, events()));
  });
  legacy_pre_effect(() => get(weeks), () => {
    set(maxEvents, Math.max(1, ...get(weeks).map((week) => week.events)));
  });
  legacy_pre_effect(() => get(weeks), () => {
    set(maxClaims, Math.max(1, ...get(weeks).map((week) => week.claims)));
  });
  legacy_pre_effect_reset();
  init();
  var fragment = comment();
  var node = first_child(fragment);
  {
    var consequent = ($$anchor2) => {
      var div = root_24();
      var div_1 = child(div);
      var div_2 = sibling(child(div_1));
      each(div_2, 5, () => get(weeks), index, ($$anchor3, week) => {
        var button = root4();
        var span = child(button);
        var span_1 = only_child(span);
        reset(button);
        template_effect(
          ($0) => {
            set_attribute2(button, "title", (get(week), untrack(() => `${get(week).start} \xB7 ${get(week).covered}/${get(week).events} Events \u6709 Source`)));
            set_attribute2(button, "aria-label", (get(week), untrack(() => `${get(week).start}\uFF1A${get(week).covered}/${get(week).events} Events \u6709 Source`)));
            set_style(span, $0);
            set_style(span_1, (get(week), untrack(() => `height:${get(week).events ? get(week).covered / get(week).events * 100 : 0}%`)));
          },
          [
            () => (get(week), get(maxEvents), untrack(() => `height:${Math.max(2, get(week).events / get(maxEvents) * 48)}px`))
          ]
        );
        event("click", button, () => openWeek()(get(week).start));
        append($$anchor3, button);
      });
      reset(div_2);
      next();
      reset(div_1);
      var div_3 = sibling(div_1, 2);
      var div_4 = sibling(child(div_3));
      each(div_4, 5, () => get(weeks), index, ($$anchor3, week) => {
        var button_1 = root_15();
        var span_2 = child(button_1);
        var span_3 = child(span_2);
        var span_4 = sibling(span_3);
        reset(span_2);
        reset(button_1);
        template_effect(
          ($0, $1, $2) => {
            set_attribute2(button_1, "title", $0);
            set_attribute2(button_1, "aria-label", (get(week), untrack(() => `${get(week).start}\uFF1A${get(week).claims} \u6761 Event\u2013Claim \u5173\u8054`)));
            set_style(span_2, $1);
            set_style(span_3, (get(week), untrack(() => `height:${get(week).claims ? (get(week).claimStates.uncertain || 0) / get(week).claims * 100 : 0}%`)));
            set_style(span_4, $2);
          },
          [
            () => (get(week), untrack(() => `${get(week).start} \xB7 ${get(week).claims} \u6761 Event\u2013Claim \u5173\u8054 \xB7 ${Object.entries(get(week).claimStates).map(([state2, count]) => `${state2} ${count}`).join(" / ") || "\u65E0 Claim"}`)),
            () => (get(week), get(maxClaims), untrack(() => `height:${Math.max(2, get(week).claims / get(maxClaims) * 48)}px`)),
            () => (get(week), untrack(() => `height:${get(week).claims ? ["contested", "corrected", "superseded", "retracted"].reduce((sum, state2) => sum + (get(week).claimStates[state2] || 0), 0) / get(week).claims * 100 : 0}%`))
          ]
        );
        event("click", button_1, () => openWeek()(get(week).start));
        append($$anchor3, button_1);
      });
      reset(div_4);
      next();
      reset(div_3);
      reset(div);
      append($$anchor2, div);
    };
    if_block(node, ($$render) => {
      if (get(weeks), untrack(() => get(weeks).length)) $$render(consequent);
    });
  }
  append($$anchor, fragment);
  pop();
}

// src/Dashboard.svelte
var root5 = from_html(`<button> </button>`);
var root_16 = from_html(`<div class="wh-search-error"> </div>`);
var root_25 = from_html(`<button><span class="wh-badge"> </span><strong> </strong><small> </small></button>`);
var root_33 = from_html(`<div class="wh-search-results"><!><!></div>`);
var root_43 = from_html(`<option> </option>`);
var root_53 = from_html(`<div class="wh-filters"><label>\u8D77\u59CB <input type="date"/></label><label>\u7ED3\u675F <input type="date"/></label><label>\u72B6\u6001 <select><option>\u5168\u90E8</option><!></select></label><label>\u4F18\u5148\u7EA7 <select><option>\u5168\u90E8</option><!></select></label><label>Thread <select><option>\u5168\u90E8</option><!></select></label><label>Entity <select><option>\u5168\u90E8</option><!></select></label><label>Location <select><option>\u5168\u90E8</option><!></select></label><label>Claim <select><option>\u5168\u90E8</option><!></select></label></div>`);
var root_63 = from_html(`<div class="wh-alert"> <button>\u6784\u5EFA\u8BFB\u6A21\u578B</button><button>\u8BBE\u7F6E\u8DEF\u5F84</button></div>`);
var root_73 = from_html(`<div class="wh-alert wh-warning"> <button>\u91CD\u65B0\u6784\u5EFA</button></div>`);
var root_83 = from_html(`<div class="wh-alert wh-warning">Chronicle \u6570\u636E\u6BD4\u5F53\u524D\u8BFB\u6A21\u578B\u66F4\u65B0\u3002<button>\u5237\u65B0</button></div>`);
var root_92 = from_html(`<span> </span>`);
var root_102 = from_html(`<button> <!></button>`);
var root_112 = from_html(`<div class="wh-empty">\u5F53\u524D\u8303\u56F4\u6CA1\u6709 Thread\u3002<button>\u6E05\u9664\u7B5B\u9009</button></div>`);
var root_123 = from_html(`<span title="Claim \u5DF2\u4FEE\u6B63">\u21BA \u4FEE\u6B63</span>`);
var root_132 = from_html(`<span title="Claim \u6709\u4E89\u8BAE">\u21C4 \u4E89\u8BAE</span>`);
var root_142 = from_html(`<span title="Claim \u5DF2\u64A4\u56DE">\u2298 \u64A4\u56DE</span>`);
var root_152 = from_html(`<span title="\u672A\u89E3\u95EE\u9898"> </span>`);
var root_162 = from_html(`<div class="wh-attention"> </div>`);
var root_17 = from_html(`<div role="button" tabindex="0"><div class="wh-row-head"><strong> </strong><span class="wh-badge"> </span><span class="wh-badge"> </span></div> <p> </p> <div class="wh-motion-signals"><!><span class="wh-change-markers" aria-label="\u72B6\u6001\u53D8\u5316"><!><!><!><!></span></div> <!> <small> </small></div>`);
var root_18 = from_html(`<aside class="wh-sidebar"><h3>Saved Views</h3><!><p> </p></aside> <section class="wh-content wh-observatory"><div class="wh-observatory-strip" aria-label="\u6700\u8FD1 7 \u5929\u7684\u5386\u53F2\u52A8\u5411"><div><small>Needs Attention</small><strong> </strong><span>\u9700\u8981\u6838\u67E5\u7684 Thread</span></div><div><small>Events \xB7 7d</small><strong> </strong><span>\u6309 Event \u65F6\u95F4\u7EDF\u8BA1</span></div><div><small>Changed Threads \xB7 7d</small><strong> </strong><span>\u6700\u8FD1\u6709\u610F\u4E49\u53D8\u66F4</span></div><div><small>Open Questions</small><strong> </strong><span>\u5F53\u524D\u8303\u56F4\u5185\u672A\u89E3</span></div></div> <div class="wh-section-bar"><h2>Threads in Motion <small> </small></h2><label>\u6392\u5E8F <select><option>\u9700\u5173\u6CE8</option><option>\u6700\u8FD1\u6709\u610F\u4E49\u53D8\u66F4</option><option>\u4F18\u5148\u7EA7</option><option>\u6807\u9898</option><option>\u8DDF\u8E2A\u5F00\u59CB</option></select></label></div> <!> <!></section>`, 1);
var root_19 = from_html(`<div class="wh-chips">\u5BA1\u8BA1\u5F15\u7528\uFF1A<!></div>`);
var root_20 = from_html(`<button class="wh-event-link">\u67E5\u770B\u7EFC\u5408\u8BB0\u5F55</button>`);
var root_21 = from_html(`<div class="wh-attention">\u65B0 Event \u665A\u4E8E\u5F53\u524D\u72B6\u6001\u7EFC\u5408\u3002</div>`);
var root_222 = from_html(`<p> </p><small> </small><!><!><!>`, 1);
var root_232 = from_html(`<p class="wh-muted">Chronicle \u5C1A\u65E0 Current State \u8BB0\u5F55\u3002</p>`);
var root_242 = from_html(`<p class="wh-annotation"> </p><small>\u4EBA\u5DE5\u6279\u6CE8 \xB7 <button>\u6253\u5F00\u6E90\u7B14\u8BB0</button></small>`, 1);
var root_252 = from_html(`<section class="wh-card"><h3>Manual annotations</h3><!></section>`);
var root_26 = from_html(`<div class="wh-subrow"><strong> </strong><small> <button class="wh-canonical-link">\u67E5\u770B\u8BB0\u5F55</button></small></div>`);
var root_27 = from_html(`<p class="wh-muted">\u6CA1\u6709\u672A\u89E3\u95EE\u9898\u3002</p>`);
var root_28 = from_html(`<button class="wh-event-link">\u67E5\u770B\u56DE\u7B54 Event</button>`);
var root_29 = from_html(`<div class="wh-subrow"> <!></div>`);
var root_30 = from_html(`<div class="wh-subrow"><button> </button><small> </small></div>`);
var root_31 = from_html(`<p class="wh-muted">\u6CA1\u6709\u663E\u5F0F\u5173\u8054\u3002</p>`);
var root_322 = from_html(`<button class="wh-event-link"> </button>`);
var root_332 = from_html(`<section class="wh-card"><h3>Current State</h3><!></section><!><section class="wh-card"><h3>Event activity</h3><!><p class="wh-muted">\u6700\u8FD1 12 \u5468\uFF0C\u4EE5\u6700\u65B0 Event \u6240\u5728\u5468\u4E3A\u7EC8\u70B9\uFF1B\u6309\u53D1\u751F\u65E5\u671F\u3001\u6BCF\u5468\u8BA1\u6570\u3002</p><!></section><section class="wh-card"><h3>Open Questions <span> </span></h3><!><details><summary>\u5DF2\u56DE\u7B54\u53CA\u5176\u4ED6\u95EE\u9898</summary><!></details></section><section class="wh-card"><h3>Entities</h3><div class="wh-chips"></div></section><section class="wh-card"><h3>Related Threads</h3><!></section><section class="wh-card"><h3>Recent Events</h3><!></section>`, 1);
var root_34 = from_html(`<span class="wh-event-state">\u21BA Claim \u4FEE\u6B63</span>`);
var root_35 = from_html(`<span class="wh-event-state">\u21C4 Claim \u4E89\u8BAE</span>`);
var root_36 = from_html(`<button class="wh-event-link">\u6253\u5F00\u6E90\u7B14\u8BB0</button>`);
var root_37 = from_html(`<small> </small>`);
var root_38 = from_html(`<button class="wh-canonical-link">Source \u8BB0\u5F55</button>`);
var root_39 = from_html(`<a target="_blank" rel="noopener noreferrer">\u6253\u5F00\u6765\u6E90 \u2197</a>`);
var root_40 = from_html(`<div class="wh-claim"><strong> </strong> <!><button class="wh-canonical-link">Claim \u8BB0\u5F55</button><small> <!> <!></small></div>`);
var root_41 = from_html(`<div class="wh-annotation"> <button class="wh-canonical-link">\u6253\u5F00\u6E90\u7B14\u8BB0</button></div>`);
var root_422 = from_html(`<div class="wh-event-meta">\u270E \u6240\u5C5E Thread \u7684\u4EBA\u5DE5\u6279\u6CE8\uFF08\u4E0D\u5F52\u5C5E\u4E8E\u6B64 Event\uFF09</div><!>`, 1);
var root_432 = from_html(`<div><span></span><div><button class="wh-title-link"> </button><!><!><small> </small></div><p> </p><details><summary>\u8BC1\u636E\u4E0E\u5143\u6570\u636E</summary><div class="wh-event-meta"> </div><div class="wh-chips"><!><!></div><small> </small><button class="wh-event-link">\u67E5\u770B Chronicle \u8BB0\u5F55</button><!><!><!></details></div>`);
var root_44 = from_html(`<div class="wh-empty">\u5F53\u524D\u8303\u56F4\u6CA1\u6709 Event\u3002<button>\u6E05\u9664\u7B5B\u9009</button></div>`);
var root_45 = from_html(`<button class="wh-load-more">\u518D\u52A0\u8F7D 100 \u4E2A Event</button>`);
var root_46 = from_html(`<!><!>`, 1);
var root_47 = from_html(`<div class="wh-location-list"></div>`);
var root_48 = from_html(`<div class="wh-empty">\u6B64 Thread \u6CA1\u6709\u5E26\u660E\u786E\u5750\u6807\u7684 Event \u5730\u70B9\u3002</div>`);
var root_49 = from_html(`<div class="wh-card"><h3>Thread Map</h3><!><!></div>`);
var root_50 = from_html(`<div class="wh-card"><h3>Thread Graph</h3><!><button>\u6253\u5F00\u4EA4\u4E92\u56FE\u8C31 \u2192</button><p class="wh-muted">\u4EE5\u5F53\u524D Thread \u4E3A\u4E2D\u5FC3\uFF0C\u9010\u6B65\u5C55\u5F00\u5173\u7CFB\u3002</p></div>`);
var root_51 = from_html(`<section class="wh-content wh-detail"><div class="wh-section-bar"><div><button>\u2190 \u8FD4\u56DE</button><h2> </h2><span class="wh-badge"> </span><span class="wh-badge"> </span></div><div><button>\u6253\u5F00\u6E90\u7B14\u8BB0</button><button>\u67E5\u770B Chronicle \u8BB0\u5F55</button></div></div><div class="wh-meta"> </div><div class="wh-tabs"></div> <!></section>`);
var root_522 = from_html(`<button class="wh-period-toggle"> </button>`);
var root_532 = from_html(`<span class="wh-event-state" title="\u6B64 Event \u6709\u4FEE\u6B63\u3001\u53D6\u4EE3\u6216\u64A4\u56DE\u7684 Claim">\u21BA Claim \u4FEE\u6B63</span>`);
var root_54 = from_html(`<span class="wh-event-state" title="\u6B64 Event \u6709\u4E89\u8BAE\u7684 Claim">\u21C4 Claim \u4E89\u8BAE</span>`);
var root_55 = from_html(`<p> </p>`);
var root_56 = from_html(`<a target="_blank" rel="noopener noreferrer">\u6765\u6E90 \u2197</a>`);
var root_57 = from_html(`<div class="wh-claim"><strong> </strong> <small> <!></small><button class="wh-canonical-link">Claim \u8BB0\u5F55</button></div>`);
var root_58 = from_html(`<div class="wh-event-meta"> </div><!>`, 1);
var root_59 = from_html(`<button>\u5728 Map \u9AD8\u4EAE</button>`);
var root_60 = from_html(`<div class="wh-timeline-expanded"><div class="wh-event-meta"> </div> <p> </p><div class="wh-chips"><!><!></div> <!> <!><div class="wh-timeline-actions"><button>Event \u8BB0\u5F55</button><button>\u5728 Graph \u9AD8\u4EAE</button><!></div></div>`);
var root_61 = from_html(`<div role="button" tabindex="0"><div class="wh-time"><span></span> </div><div><strong> </strong><!><!><small> </small><!><small> </small></div><button>\u6253\u5F00 \u2192</button><!></div>`);
var root_622 = from_html(`<h3 class="wh-group"><!> <span class="wh-density-bar"></span><small> </small></h3><!>`, 1);
var root_632 = from_html(`<div class="wh-timeline-pager"><button>\u2190 \u8F83\u65B0\u7684 Events</button><span> </span><button>\u8F83\u65E9\u7684 Events \u2192</button></div>`);
var root_64 = from_html(`<section class="wh-content wh-wide"><div class="wh-section-bar"><h2>Timeline <small> </small></h2><div><div class="wh-range-switch" aria-label="Timeline \u65F6\u95F4\u8303\u56F4"></div><label>\u5206\u7EC4 <select><option>\u65E5\u671F</option><option>Thread</option><option>Entity</option></select></label><label>\u5BC6\u5EA6 <select><option>\u6807\u51C6</option><option>\u7D27\u51D1</option></select></label></div></div><!><!><!></section>`);
var root_65 = from_html(`<div class="wh-empty">\u5F53\u524D\u8303\u56F4\u6CA1\u6709 Entity\u3002<button>\u6E05\u9664\u7B5B\u9009</button></div>`);
var root_66 = from_html(`<button class="wh-entity-row"><strong> </strong><span class="wh-badge"> </span><span class="wh-entity-top"> </span><!><small> </small></button>`);
var root_67 = from_html(`<p class="wh-muted">\u663E\u793A\u524D 500 \u4E2A Entity\u3002\u8BF7\u4F7F\u7528\u641C\u7D22\u7F29\u5C0F\u8303\u56F4\u3002</p>`);
var root_68 = from_html(`<section class="wh-content wh-wide"><div class="wh-section-bar"><h2>Entities <small> </small></h2><div><label>\u7C7B\u578B <select><option>\u5168\u90E8</option><!></select></label><label>\u6700\u5C11 Events <input type="number" min="0" max="10000"/></label></div></div><!><div class="wh-entity-grid"></div><!></section>`);
var root_69 = from_html(`<p class="wh-muted">\u6CA1\u6709\u6D3B\u8DC3\u7684\u5173\u8054 Thread\u3002</p>`);
var root_70 = from_html(`<p class="wh-muted">\u6CA1\u6709\u5173\u8054 Thread\u3002</p>`);
var root_71 = from_html(`<p class="wh-muted">\u6CA1\u6709\u663E\u5F0F Entity \u5173\u7CFB\u3002</p>`);
var root_722 = from_html(`<div class="wh-subrow"><strong> </strong><button> </button></div>`);
var root_732 = from_html(`<section class="wh-card"><h3>Current involvement</h3><!></section><section class="wh-card"><h3>Threads</h3><!></section><section class="wh-card"><h3>Event Activity</h3><!><p class="wh-muted">\u6700\u8FD1 12 \u5468\uFF0C\u4EE5\u6700\u65B0 Event \u6240\u5728\u5468\u4E3A\u7EC8\u70B9\uFF1B\u6309\u53D1\u751F\u65E5\u671F\u3001\u6BCF\u5468\u8BA1\u6570\u3002</p><!></section><section class="wh-card"><h3>Related Entities</h3><div class="wh-chips"></div></section><section class="wh-card"><h3>Thread questions (context)</h3><p class="wh-muted">\u4EE5\u4E0B\u95EE\u9898\u5C5E\u4E8E\u5173\u8054 Thread\uFF0C\u4E0D\u8868\u793A\u95EE\u9898\u76F4\u63A5\u5173\u4E8E\u6B64 Entity\u3002</p><!></section>`, 1);
var root_74 = from_html(`<section class="wh-card"><h3>Entity Map</h3><!></section>`);
var root_75 = from_html(`<section class="wh-card"><h3>Entity Graph</h3><!><button>\u6253\u5F00\u4EA4\u4E92\u56FE\u8C31 \u2192</button></section>`);
var root_76 = from_html(`<section class="wh-content wh-detail"><div class="wh-section-bar"><div><button>\u2190 \u8FD4\u56DE</button><h2> </h2><span class="wh-badge"> </span></div><button>\u67E5\u770B Chronicle \u8BB0\u5F55</button></div><div class="wh-meta"> </div><div class="wh-tabs"></div><!></section>`);
var root_77 = from_html(`<div class="wh-empty">\u5F53\u524D\u8303\u56F4\u6CA1\u6709\u5DF2\u5730\u7406\u7F16\u7801\u7684 Event\u3002Chronicle \u5FEB\u7167\u6CA1\u6709 Event \u5730\u70B9\u5750\u6807\uFF1B\u4EC5\u63A5\u53D7\u6709\u660E\u786E\u53D1\u751F\u5730\u8BC1\u636E\u548C\u7CBE\u5EA6\u7684\u5730\u70B9\u3002<button>\u6E05\u9664\u7B5B\u9009</button></div>`);
var root_78 = from_svg(`<line y1="0" y2="450" class="wh-map-grid"></line>`);
var root_79 = from_svg(`<line x1="0" x2="900" class="wh-map-grid"></line>`);
var root_80 = from_svg(`<g role="button" tabindex="0"><title> </title><circle></circle><text text-anchor="middle" dy="4"> </text></g>`);
var root_81 = from_html(`<div class="wh-map"><svg viewBox="0 0 900 450" role="img" aria-label="\u5730\u7406\u4E8B\u4EF6\u5206\u5E03"><rect x="0" y="0" width="900" height="450" class="wh-map-bg"></rect><g><path class="wh-world-shape"></path><!><!><!></g></svg><p class="wh-muted">\u7ECF\u7EAC\u7F51\u4E0E\u5750\u6807\u6765\u81EA\u672C\u5730\u8BFB\u6A21\u578B\u3002\u5706\u70B9\u805A\u5408\u968F\u7F29\u653E\u53D8\u5316\uFF1B\u5730\u70B9\u7CBE\u5EA6\u89C1\u68C0\u67E5\u5668\u3002</p></div>`);
var root_822 = from_html(`<section class="wh-content wh-wide"><div class="wh-section-bar"><h2>Map <small> </small></h2><div><label>\u6A21\u5F0F <select><option>Events</option><option>Threads</option><option>Entities</option></select></label><button>\uFF0B</button><button>\uFF0D</button><button>\u91CD\u7F6E</button></div></div><!></section>`);
var root_832 = from_html(`<label><input type="checkbox"/> </label>`);
var root_84 = from_html(`<button>\u6E05\u9664\u5173\u7CFB\u8FC7\u6EE4</button>`);
var root_85 = from_html(` <button>\u91CD\u5EFA\u8BFB\u6A21\u578B</button>`, 1);
var root_86 = from_html(`\u5F53\u524D\u8303\u56F4\u6CA1\u6709\u5173\u7CFB\u56FE\u8282\u70B9\u3002<button>\u6E05\u9664\u7B5B\u9009</button>`, 1);
var root_87 = from_html(`<div class="wh-empty"><!></div>`);
var root_88 = from_svg(`<line role="button" tabindex="0"><title> </title></line>`);
var root_89 = from_svg(`<rect x="-15" y="-10" width="30" height="20" rx="6" class="wh-node-thread"></rect>`);
var root_90 = from_svg(`<polygon></polygon>`);
var root_91 = from_svg(`<rect x="-8" y="-10" width="16" height="20" class="wh-node-source"></rect>`);
var root_922 = from_svg(`<circle r="9" class="wh-node-question"></circle>`);
var root_93 = from_svg(`<circle></circle>`);
var root_94 = from_svg(`<text y="-17" text-anchor="middle"> </text>`);
var root_95 = from_svg(`<g role="button" tabindex="0"><!><!><title> </title></g>`);
var root_96 = from_html(`<div class="wh-graph"><svg viewBox="0 0 700 500" role="img" aria-label="\u7C7B\u578B\u5316\u5173\u7CFB\u56FE"><!><!></svg></div>`);
var root_97 = from_html(`<section class="wh-content wh-wide"><div class="wh-section-bar"><h2>Graph <small> </small></h2><div><label>\u9884\u8BBE <select><option>Thread relationships</option><option>Entity network</option><option>Event\u2013Entity network</option><option>Evidence chain</option><option>Full scoped graph</option></select></label><label>\u5E03\u5C40 <select><option>\u5F84\u5411</option><option>\u9759\u6001\u529B\u5BFC\u5411</option><option>\u8BC1\u636E\u5C42\u7EA7</option></select></label><label>\u6DF1\u5EA6 <select><option>1</option><option>2</option><option>3</option></select></label><label>\u8282\u70B9\u4E0A\u9650 <input type="number" min="5" max="150"/></label><button>\u91CD\u7F6E\u5E03\u5C40</button></div></div><div class="wh-graph-controls"><span>\u8282\u70B9</span><!><span>\u5173\u7CFB</span><select><option>\u9009\u62E9\u5173\u7CFB\u7C7B\u578B</option><!></select><!><input type="search" placeholder="\u641C\u7D22\u8282\u70B9"/></div><div class="wh-graph-legend">\u25A2 Thread \xB7 \u25CF Event \xB7 \u25C9 Entity \xB7 \u25C7 Claim / Location \xB7 \u25A1 Source \xB7 \u25CB Question\u3000\u5B9E\u7EBF\uFF1AChronicle Relation\uFF1B\u865A\u7EBF\uFF1A\u6295\u5F71\u7ED3\u6784\u5173\u7CFB</div><!></section>`);
var root_98 = from_html(`<button>\u67E5\u770B\u5173\u7CFB\u8BB0\u5F55</button>`);
var root_99 = from_html(`<h3> </h3><p> </p><p> </p><p> </p><p> </p><p>\u5173\u7CFB\u6709\u6548\u671F\uFF1AChronicle \u672A\u63D0\u4F9B</p><!>`, 1);
var root_100 = from_html(`<p class="wh-graph-summary"> </p>`);
var root_101 = from_html(`<button>\u6309 Entity \u7B5B\u9009 Timeline</button><button>\u6309 Entity \u7B5B\u9009 Threads</button>`, 1);
var root_1022 = from_html(`<button>\u67E5\u770B Chronicle \u8BB0\u5F55</button>`);
var root_103 = from_html(`<h3> </h3><p> </p><!><!><!><!><p> </p><h4>\u5F53\u524D\u56FE\u5185\u5173\u7CFB</h4><!><button> </button><button>\u9690\u85CF\u8282\u70B9</button><button> </button><button>\u6253\u5F00\u5BF9\u8C61</button><!><!>`, 1);
var root_104 = from_html(`<span>\u2014</span>`);
var root_105 = from_html(`<button>\u67E5\u770B\u5730\u70B9\u6765\u6E90</button>`);
var root_106 = from_html(`<h3> </h3><!><p> </p><p> </p><p> </p><p> </p><p>Entities\uFF1A</p><div class="wh-chips"></div><!><h4>\u6700\u8FD1 Events</h4><!><button>\u5728 Timeline \u67E5\u770B</button><button>\u7B5B\u9009 Threads</button><button>\u5728 Graph \u9AD8\u4EAE\u5730\u70B9</button><!>`, 1);
var root_107 = from_html(`<button class="wh-question-preview"> </button>`);
var root_108 = from_html(`<div class="wh-visual-inspector"><small>VISUAL INSPECTOR</small><h3> </h3><p class="wh-inspector-state"> </p><div class="wh-inspector-switch" aria-label="Thread \u6295\u5F71"></div><!><h4> </h4><!><h4>Latest material change</h4><p class="wh-latest-change"> </p><button class="wh-primary-action">\u6253\u5F00 Thread \u2192</button><button>\u6253\u5F00\u6E90\u7B14\u8BB0</button></div>`);
var root_109 = from_html(`<button>\u5728 Map \u9AD8\u4EAE\u5730\u70B9</button>`);
var root_110 = from_html(`<h3> </h3><p> </p><p> </p><p> </p><button>\u5728 Thread \u4E2D\u6253\u5F00</button><!><button>\u5728 Graph \u9AD8\u4EAE Event</button>`, 1);
var root_111 = from_html(`<h3> </h3><p> </p><button>\u6253\u5F00 Entity</button>`, 1);
var root_1122 = from_html(`<aside><button class="wh-close">\xD7</button><!></aside>`);
var root_113 = from_html(`<!> <!> <main class="wh-main"><!> <!></main> <footer class="wh-footer"> </footer>`, 1);
var root_114 = from_html(`<div class="wh-app" tabindex="-1"><header class="wh-header"><div class="wh-brand"><strong>World Historian</strong><span>Dashboard</span></div><nav aria-label="\u4E3B\u5BFC\u822A"></nav><div class="wh-header-actions"><button title="\u540E\u9000">\u2190</button><button title="\u524D\u8FDB">\u2192</button><button title="\u5237\u65B0\u8BFB\u6A21\u578B">\u21BB</button><button title="\u8BBE\u7F6E">\u2699</button></div></header> <div class="wh-toolbar"><div class="wh-search"><input type="search" placeholder="\u641C\u7D22 Thread\u3001Event\u3001Entity\u3001Claim\u3001Source \u7B49  /"/><!></div><button> </button><span class="wh-scope"> </span><button>\u6E05\u9664\u8303\u56F4</button><small> </small></div> <!> <!></div>`);
function Dashboard($$anchor, $$props) {
  push($$props, false);
  const visibleThreads = mutable_source();
  const homeThreadId = mutable_source();
  const homeThread = mutable_source();
  const observatoryEvents = mutable_source();
  const attentionCount = mutable_source();
  const changedCount = mutable_source();
  const openQuestionCount = mutable_source();
  const visibleEvents = mutable_source();
  const timelineGroups = mutable_source();
  const visibleEntities = mutable_source();
  const currentThread = mutable_source();
  const currentEntity = mutable_source();
  const graphSlice = mutable_source();
  const graphPositions = mutable_source();
  const locationPoints = mutable_source();
  const markerClusters = mutable_source();
  const scopeCount = mutable_source();
  const inspectedEvent = mutable_source();
  const inspectedThread = mutable_source();
  const inspectedEntity = mutable_source();
  let repository = prop($$props, "repository", 8);
  let error = prop($$props, "error", 8, "");
  let stale = prop($$props, "stale", 8, false);
  let refresh = prop($$props, "refresh", 8);
  let openNote = prop($$props, "openNote", 8);
  let openCanonical = prop($$props, "openCanonical", 8);
  let searchAll = prop($$props, "searchAll", 8);
  let settings = prop($$props, "settings", 8);
  const blank = () => ({
    search: "",
    from: "",
    to: "",
    threadId: "",
    entityId: "",
    locationId: "",
    status: "",
    priority: "",
    claimState: ""
  });
  let scope = mutable_source(blank());
  let page = mutable_source("threads");
  let detailId = mutable_source("");
  let inspectorId = mutable_source("");
  let eventId = mutable_source("");
  let localContext = mutable_source(null);
  let inspectorProjection = mutable_source("Time");
  let saved = mutable_source("Recently Changed");
  let sort = mutable_source("change");
  let group = mutable_source("date");
  let density = mutable_source("normal");
  let mapMode = mutable_source("events");
  let timeRange = mutable_source("All");
  let graphPreset = mutable_source("Thread relationships");
  let graphLayout = mutable_source("radial");
  let maxNodes = mutable_source(80);
  let depth = mutable_source(1);
  let selectedNode = mutable_source("");
  let selectedEdge = mutable_source(null);
  let hidden = mutable_source(/* @__PURE__ */ new Set());
  let pinned = mutable_source(/* @__PURE__ */ new Set());
  let pinnedPositions = mutable_source(/* @__PURE__ */ new Map());
  let expanded = mutable_source(/* @__PURE__ */ new Set());
  let graphNodeTypes = mutable_source(/* @__PURE__ */ new Set(["thread", "event", "entity", "location"]));
  let graphEdgeTypes = mutable_source(/* @__PURE__ */ new Set());
  let searchInput = mutable_source();
  let appRoot = mutable_source();
  onMount(() => get(appRoot)?.focus());
  let searchFocused = mutable_source(false);
  let searchResults = mutable_source([]);
  let searchError = mutable_source("");
  let searchSeq = 0;
  let searchTimer;
  let history = mutable_source([{ page: "threads", id: "", eventId: "", scrollTop: 0 }]);
  let historyIndex = mutable_source(0);
  let sequence = "";
  let showFilters = mutable_source(false);
  let showInspector = mutable_source(false);
  let zoom = mutable_source(1);
  let mapCenter = mutable_source({ lat: 0, lon: 0 });
  let selectedLocation = mutable_source("");
  let selectedCluster = mutable_source([]);
  let entityKind = mutable_source("");
  let minimumActivity = mutable_source(0);
  let timelineStart = mutable_source(0);
  const timelineWindow = 300;
  let periodStates = /* @__PURE__ */ new Map();
  let threadEventLimit = mutable_source(100);
  let expandedEvents = mutable_source(/* @__PURE__ */ new Set());
  let graphRefresh = mutable_source(0);
  const navs = ["threads", "timeline", "entities", "map", "graph"];
  const labels = {
    threads: "Threads",
    timeline: "Timeline",
    entities: "Entities",
    map: "Map",
    graph: "Graph"
  };
  const reasons = {
    contested_or_corrected_claim: "\u5B58\u5728\u4E89\u8BAE\u6216\u4FEE\u6B63\u7684 Claim",
    high_priority_open_questions: "\u9AD8\u4F18\u5148\u7EA7\u672A\u89E3\u95EE\u9898",
    high_priority_stale: "\u9AD8\u4F18\u5148\u7EA7 Thread \u591A\u8F6E\u9759\u9ED8"
  };
  const stateGlyph = {
    supported: "\u2713",
    uncertain: "\u25B3",
    analytical: "\u25B3",
    contested: "\u21C4",
    corrected: "\u21BA",
    superseded: "\u21BA",
    retracted: "\u2298"
  };
  function rememberScroll() {
    if (get(history)[get(historyIndex)]) mutate(history, get(history)[get(historyIndex)].scrollTop = get(appRoot)?.querySelector(".wh-content")?.scrollTop || 0);
  }
  function restoreScroll(value) {
    tick().then(() => {
      const pane = get(appRoot)?.querySelector(".wh-content");
      if (pane) pane.scrollTop = value || 0;
    });
  }
  function navigate(next2, id = "", extra = {}) {
    rememberScroll();
    if (next2 === "thread" && get(page) === "threads") set(threadProjection, get(inspectorProjection) === "Time" ? "Timeline" : get(inspectorProjection));
    set(page, next2);
    set(detailId, id);
    set(localContext, extra.localContext || null);
    set(inspectorId, "");
    set(eventId, extra.eventId || "");
    if (get(eventId)) set(expandedEvents, /* @__PURE__ */ new Set([...get(expandedEvents), get(eventId)]));
    set(threadEventLimit, 100);
    set(showInspector, false);
    set(history, get(history).slice(0, get(historyIndex) + 1));
    get(history).push({
      page: next2,
      id,
      eventId: get(eventId),
      localContext: get(localContext),
      scrollTop: 0
    });
    set(historyIndex, get(history).length - 1);
  }
  function back() {
    if (get(historyIndex) > 0) {
      rememberScroll();
      update(historyIndex, -1);
      const h = get(history)[get(historyIndex)];
      set(page, h.page);
      set(detailId, h.id);
      set(eventId, h.eventId);
      set(localContext, h.localContext || null);
      restoreScroll(h.scrollTop);
    }
  }
  function forward() {
    if (get(historyIndex) < get(history).length - 1) {
      rememberScroll();
      update(historyIndex);
      const h = get(history)[get(historyIndex)];
      set(page, h.page);
      set(detailId, h.id);
      set(eventId, h.eventId);
      set(localContext, h.localContext || null);
      restoreScroll(h.scrollTop);
    }
  }
  function setScope(key2, value) {
    set(scope, { ...get(scope), [key2]: value });
    set(timelineStart, 0);
  }
  function setTimeRange(value) {
    set(timeRange, value);
    if (value === "Custom") {
      set(showFilters, true);
      return;
    }
    const days = { "7d": 7, "30d": 30, "90d": 90, "1y": 365 }[value];
    set(scope, {
      ...get(scope),
      from: days ? new Date(Date.now() - (days - 1) * 864e5).toISOString().slice(0, 10) : "",
      to: ""
    });
    set(timelineStart, 0);
  }
  function timeNumber(value) {
    return value ? Date.parse(value) || 0 : 0;
  }
  function clearScope() {
    set(scope, blank());
    set(saved, "Recently Changed");
    set(timeRange, "All");
    set(timelineStart, 0);
  }
  function applySaved(name) {
    set(saved, name);
    set(scope, { ...get(scope), status: "", priority: "" });
    if (name === "Active") setScope("status", "active");
    if (name === "Watching") setScope("status", "watching");
    if (name === "Dormant") setScope("status", "dormant");
    if (name === "Resolved") setScope("status", "resolved");
  }
  function sortedThreads(list) {
    let result = [...list];
    if (get(saved) === "Attention") result = result.filter((t) => t.attention.required);
    if (get(saved) === "Open Questions") result = result.filter((t) => t.open_question_count);
    if (get(saved) === "Stale") result = result.filter((t) => t.stale);
    const priority = { high: 0, normal: 1, low: 2 };
    return result.sort((a, b) => get(sort) === "title" ? a.title.localeCompare(b.title) : get(sort) === "priority" ? priority[a.priority] - priority[b.priority] || a.title.localeCompare(b.title) : get(sort) === "tracking" ? timeNumber(a.tracking_since) - timeNumber(b.tracking_since) : get(sort) === "attention" ? Number(b.attention.required) - Number(a.attention.required) || timeNumber(b.last_meaningful_change_at) - timeNumber(a.last_meaningful_change_at) : timeNumber(b.last_meaningful_change_at) - timeNumber(a.last_meaningful_change_at));
  }
  function dateOf(e) {
    return e.occurred_at || e.reported_at || e.first_observed_at || "\u672A\u77E5";
  }
  function dateLabel(e) {
    return e.occurred_at ? `${e.occurred_at} \xB7 ${e.time_precision}` : `${dateOf(e)} \xB7 \u53D1\u751F\u65F6\u95F4\u672A\u77E5\uFF08\u6309\u62A5\u9053/\u89C2\u5BDF\u6392\u5E8F\uFF09`;
  }
  function openRef(ref) {
    if (ref?.obsidian_path) openNote()(ref.obsidian_path);
  }
  function threadName(id) {
    return repository()?.threadById.get(id)?.title || id;
  }
  function entityName(id) {
    return repository()?.entityById.get(id)?.name || id;
  }
  function openEvent(e) {
    if (e.thread_ids?.length) navigate("thread", e.thread_ids[0], { eventId: e.event_id });
    else {
      navigate("timeline");
      set(inspectorId, e.event_id);
      set(showInspector, true);
    }
  }
  function updateSearch(value) {
    setScope("search", value);
    const sequence2 = ++searchSeq;
    clearTimeout(searchTimer);
    set(searchError, "");
    set(searchResults, value.trim() && repository() && !searchAll() ? repository().search(value) : []);
    if (value.trim() && repository() && searchAll()) searchTimer = setTimeout(
      () => searchAll()(value).then((hits) => {
        if (sequence2 === searchSeq) set(searchResults, hits);
      }).catch(() => {
        if (sequence2 === searchSeq) set(searchError, "\u641C\u7D22\u7D22\u5F15\u4E0D\u53EF\u7528\uFF0C\u8BF7\u5237\u65B0\u8BFB\u6A21\u578B");
      }),
      180
    );
  }
  function openSearchHit(hit) {
    set(searchFocused, false);
    searchSeq++;
    clearTimeout(searchTimer);
    set(scope, { ...get(scope), search: "" });
    set(searchResults, []);
    set(searchError, "");
    if (hit.type === "thread") navigate("thread", hit.id);
    else if (hit.type === "entity") navigate("entity", hit.id);
    else if (hit.type === "location") showLocation(hit.id);
    else if (hit.type === "question" && hit.owner_thread_id) {
      navigate("thread", hit.owner_thread_id);
      set(threadProjection, "Overview");
    } else if (hit.type === "event" || hit.owner_event_id) {
      const event2 = repository().eventById.get(hit.type === "event" ? hit.id : hit.owner_event_id);
      if (event2) {
        openEvent(event2);
        set(threadProjection, "Timeline");
      } else openCanonical()({
        kind: "chronicle",
        table: hit.type === "question" ? "open_questions" : hit.type + "s",
        id: hit.id
      });
    } else openCanonical()({
      kind: "chronicle",
      table: hit.type === "question" ? "open_questions" : hit.type + "s",
      id: hit.id
    });
  }
  function inspectEvent(id) {
    set(inspectorId, id);
    set(showInspector, true);
  }
  function toggleEventDetail(id, open) {
    const next2 = new Set(get(expandedEvents));
    open ? next2.add(id) : next2.delete(id);
    set(expandedEvents, next2);
  }
  function keyboard(event2) {
    if (!get(appRoot)?.contains(document.activeElement)) return;
    if (event2.target instanceof HTMLInputElement || event2.target instanceof HTMLSelectElement || event2.target instanceof HTMLTextAreaElement) return;
    if (event2.key === "/") {
      event2.preventDefault();
      get(searchInput)?.focus();
      return;
    }
    if (event2.key === "Escape") {
      if (get(showInspector)) {
        set(showInspector, false);
        set(inspectorId, "");
      } else if (["thread", "entity"].includes(get(page))) back();
      return;
    }
    if (event2.key === "r") {
      refresh()();
      return;
    }
    if (event2.key === "g") {
      sequence = "g";
      setTimeout(() => sequence = "", 900);
      return;
    }
    if (sequence === "g") {
      const dest = {
        t: "threads",
        l: "timeline",
        e: "entities",
        m: "map",
        g: "graph"
      }[event2.key];
      sequence = "";
      if (dest) {
        navigate(dest);
        return;
      }
    }
    if (event2.key === "j" || event2.key === "ArrowDown" || event2.key === "k" || event2.key === "ArrowUp") {
      const items = get(page) === "threads" ? sortedThreads(repository().filteredThreads(get(scope))).map((t) => t.thread_id) : get(page) === "timeline" ? repository().filteredEvents(get(scope)).map((e) => e.event_id) : get(page) === "entities" ? repository().filteredEntities(get(scope)).map((e) => e.entity_id) : [];
      if (!items.length) return;
      event2.preventDefault();
      let idx = items.indexOf(get(inspectorId));
      idx = Math.max(0, Math.min(items.length - 1, idx + (event2.key === "j" || event2.key === "ArrowDown" ? 1 : -1)));
      set(inspectorId, items[idx]);
      set(showInspector, true);
    }
    if (event2.key === "Enter" && get(inspectorId)) {
      if (get(page) === "threads") navigate("thread", get(inspectorId));
      else if (get(page) === "timeline") openEvent(repository().eventById.get(get(inspectorId)));
      else if (get(page) === "entities") navigate("entity", get(inspectorId));
    }
  }
  function scopedGraph(_scope, _depth, _maxNodes, _selectedNode, _nodeTypes, _edgeTypes, _hidden, _expanded, _refresh, _preset, _localContext) {
    if (repository().graphFault) return { nodes: [], edges: [] };
    const unrestricted = !Object.values(get(scope)).some(Boolean);
    const scopedEvents = unrestricted ? [] : repository().filteredEvents(get(scope));
    const eventIds = unrestricted ? null : new Set(scopedEvents.map((e) => e.event_id));
    const threadIds = new Set(repository().filteredThreads(get(scope)).map((t) => t.thread_id));
    const entityIds = new Set(repository().filteredEntities(get(scope)).map((e) => e.entity_id));
    const allowed = new Set([...threadIds].map((id) => "thread:" + id));
    if (eventIds) for (const id of eventIds) allowed.add("event:" + id);
    for (const id of entityIds) allowed.add("entity:" + id);
    if (eventIds) {
      for (const location of repository().locations) if (location.event_ids.some((id) => eventIds.has(id))) allowed.add("location:" + location.location_id);
    }
    const evidence = get(graphPreset) === "Evidence chain" || get(graphPreset) === "Full scoped graph";
    if (evidence && get(selectedNode)) {
      const node = repository().graphNode(get(selectedNode));
      if (node?.type === "claim" && (unrestricted || eventIds.has(node.owner_event_id)) || node?.type === "question" && threadIds.has(node.owner_thread_id) || node?.type === "source" && repository().neighbors(get(selectedNode)).some((edge) => unrestricted || eventIds.has(repository().graphNode(edge.source)?.owner_event_id))) allowed.add(get(selectedNode));
    }
    const allows = (edge) => get(graphPreset) === "Full scoped graph" || get(graphPreset) === "Thread relationships" ? get(graphPreset) === "Full scoped graph" || edge.source.startsWith("thread:") || edge.target.startsWith("thread:") : get(graphPreset) === "Entity network" ? edge.source.startsWith("entity:") || edge.target.startsWith("entity:") : get(graphPreset) === "Event\u2013Entity network" ? ["event:", "entity:"].some((prefix) => edge.source.startsWith(prefix)) && ["event:", "entity:"].some((prefix) => edge.target.startsWith(prefix)) : [
      "event_contains_claim",
      "claim_supported_by_source",
      "thread_contains_event"
    ].includes(edge.type);
    const admissible = (id, edge, from) => unrestricted || allowed.has(id) || evidence && (id.startsWith("claim:") && edge.type === "event_contains_claim" && from.startsWith("event:") || id.startsWith("question:") && edge.type === "question_about_thread" && from.startsWith("thread:") || id.startsWith("source:") && edge.type === "claim_supported_by_source" && from.startsWith("claim:"));
    let seeds = [];
    if (get(selectedNode)) seeds = [get(selectedNode)];
    else if (get(localContext)) seeds = [get(localContext).type + ":" + get(localContext).id];
    else if (get(scope).threadId) seeds = ["thread:" + get(scope).threadId];
    else if (get(scope).entityId) seeds = ["entity:" + get(scope).entityId];
    else if (get(graphPreset) === "Entity network") seeds = [...entityIds].slice(0, 8).map((id) => "entity:" + id);
    else if (get(graphPreset) === "Event\u2013Entity network") seeds = (unrestricted ? repository().recentEvents(8) : scopedEvents.slice(0, 8)).map((event2) => "event:" + event2.event_id);
    else if (get(graphPreset) === "Evidence chain") seeds = (unrestricted ? repository().recentEvents(1) : scopedEvents.slice(0, 1)).map((event2) => "event:" + event2.event_id);
    else seeds = [...threadIds].slice(0, 8).map((id) => "thread:" + id);
    if (get(localContext)) allowed.add(get(localContext).type + ":" + get(localContext).id);
    if (unrestricted && get(selectedNode)) allowed.add(get(selectedNode));
    const cap = Math.max(5, Math.min(150, Number(get(maxNodes)) || 45));
    const selected = new Set(seeds.filter((id) => repository().graphNode(id) && (unrestricted || allowed.has(id)) && !get(hidden).has(id)));
    const edgeMap = /* @__PURE__ */ new Map();
    let frontier = [...selected];
    for (let level = 0; level < get(depth) && frontier.length && selected.size < cap; level++) {
      const next2 = [];
      for (const from of frontier) for (const edge of repository().neighbors(from)) {
        if (!allows(edge) || get(graphEdgeTypes).size && !get(graphEdgeTypes).has(edge.type)) continue;
        const candidate = edge.source === from ? edge.target : edge.source;
        if (!admissible(candidate, edge, from) || get(hidden).has(candidate)) continue;
        const node = repository().graphNode(candidate);
        if (!node || !get(graphNodeTypes).has(node.type)) continue;
        edgeMap.set(edge.id, edge);
        if (!selected.has(candidate) && selected.size < cap) {
          selected.add(candidate);
          next2.push(candidate);
        }
      }
      frontier = next2;
    }
    for (const from of get(expanded)) if (selected.has(from)) {
      let added = 0;
      for (const edge of repository().neighbors(from)) {
        if (added >= 20) break;
        if (!allows(edge)) continue;
        const candidate = edge.source === from ? edge.target : edge.source;
        if (!admissible(candidate, edge, from) || get(hidden).has(candidate)) continue;
        const node = repository().graphNode(candidate);
        if (node && get(graphNodeTypes).has(node.type) && selected.size < cap) {
          if (!selected.has(candidate)) added++;
          selected.add(candidate);
          edgeMap.set(edge.id, edge);
        }
      }
    }
    const nodes = [...selected].map((id) => ({ id, ...repository().graphNode(id) }));
    const edges = [...edgeMap.values()].filter((edge) => selected.has(edge.source) && selected.has(edge.target)).slice(0, 160);
    if (repository().graphFault) return { nodes: [], edges: [] };
    return { nodes, edges };
  }
  function layoutPositions(slice, mode, pins) {
    const nodes = slice.nodes, edges = slice.edges, result = /* @__PURE__ */ new Map();
    if (mode === "hierarchical") {
      const rank = {
        thread: 0,
        event: 1,
        entity: 1,
        location: 1,
        question: 2,
        claim: 2,
        source: 3
      };
      const columns = [[], [], [], []];
      for (const node of nodes) columns[rank[node.type] ?? 1].push(node);
      columns.forEach((column, x) => column.forEach((node, i) => result.set(node.id, { x: 80 + x * 175, y: 60 + (i + 1) * 390 / (column.length + 1) })));
    } else {
      nodes.forEach((node, i) => {
        const angle = 2 * Math.PI * i / Math.max(nodes.length, 1) - Math.PI / 2;
        result.set(node.id, {
          x: 350 + Math.cos(angle) * Math.min(255, 80 + nodes.length * 2.5),
          y: 250 + Math.sin(angle) * Math.min(185, 70 + nodes.length * 1.8)
        });
      });
      for (const [id, position] of pins) if (result.has(id)) result.set(id, { ...position });
      if (mode === "force") for (let step = 0; step < 45; step++) {
        const shifts = new Map(nodes.map((node) => [node.id, { x: 0, y: 0 }]));
        for (let i = 0; i < nodes.length; i++) for (let j = i + 1; j < nodes.length; j++) {
          const a = result.get(nodes[i].id), b = result.get(nodes[j].id), dx = a.x - b.x || 0.1, dy = a.y - b.y || 0.1, d2 = Math.max(100, dx * dx + dy * dy), force = 900 / d2;
          shifts.get(nodes[i].id).x += dx * force;
          shifts.get(nodes[i].id).y += dy * force;
          shifts.get(nodes[j].id).x -= dx * force;
          shifts.get(nodes[j].id).y -= dy * force;
        }
        for (const edge of edges) {
          const a = result.get(edge.source), b = result.get(edge.target);
          if (!a || !b) continue;
          const dx = b.x - a.x, dy = b.y - a.y;
          shifts.get(edge.source).x += dx * 0.012;
          shifts.get(edge.source).y += dy * 0.012;
          shifts.get(edge.target).x -= dx * 0.012;
          shifts.get(edge.target).y -= dy * 0.012;
        }
        for (const node of nodes) {
          if (pins.has(node.id)) continue;
          const p = result.get(node.id), d = shifts.get(node.id);
          p.x = Math.max(30, Math.min(670, p.x + d.x));
          p.y = Math.max(30, Math.min(470, p.y + d.y));
        }
      }
    }
    for (const [id, position] of pins) if (result.has(id)) result.set(id, position);
    return result;
  }
  function graphPosition(i, n, id) {
    return get(graphPositions).get(id) || { x: 350, y: 250 };
  }
  function mapPoints(_scope, _mode) {
    if (!repository().locations.length) return [];
    const events = repository().filteredEvents(get(scope));
    const eventIds = new Set(events.map((e) => e.event_id));
    return repository().locations.filter((l) => (!get(scope).locationId || l.location_id === get(scope).locationId) && l.event_ids.some((id) => eventIds.has(id))).map((l) => {
      const scoped = l.event_ids.filter((id) => eventIds.has(id));
      const count = get(mapMode) === "threads" ? new Set(scoped.flatMap((id) => repository().eventById.get(id)?.thread_ids || [])).size : get(mapMode) === "entities" ? new Set(scoped.flatMap((id) => repository().eventById.get(id)?.entity_ids || [])).size : scoped.length;
      return { ...l, count };
    });
  }
  function visibleMapPoints(points, scale, center) {
    if (scale === 1) return points;
    return points.filter((location) => Math.abs((location.lon - center.lon + 540) % 360 - 180) <= 180 / scale && Math.abs(location.lat - center.lat) <= 90 / scale);
  }
  function clusters(points, scale) {
    const cells = /* @__PURE__ */ new Map();
    const gridFactor = Math.max(1, Math.ceil(Math.sqrt(points.length / 400)));
    for (const l of points) {
      const cell = scale >= 4 && points.length <= 400 ? `location:${l.location_id}` : scale <= 2 && l.country_code ? `country:${l.country_code}` : scale <= 2 && l.region ? `region:${l.region}` : `grid:${Math.round(l.lon / (25 * gridFactor / scale))}:${Math.round(l.lat / (20 * gridFactor / scale))}`;
      const group2 = cells.get(cell) || [];
      group2.push(l);
      cells.set(cell, group2);
    }
    return [...cells.values()].map((group2) => ({
      locations: group2,
      lon: group2.reduce((s, l) => s + l.lon, 0) / group2.length,
      lat: group2.reduce((s, l) => s + l.lat, 0) / group2.length,
      count: group2.reduce((s, l) => s + l.count, 0)
    }));
  }
  function graphChooseNode(id) {
    set(selectedNode, id);
    set(selectedEdge, null);
    set(inspectorId, id);
    set(showInspector, true);
  }
  function graphChooseEdge(edge) {
    set(selectedEdge, edge);
    set(selectedNode, "");
    set(showInspector, true);
  }
  function toggleType(type) {
    const next2 = new Set(get(graphNodeTypes));
    next2.has(type) ? next2.delete(type) : next2.add(type);
    set(graphNodeTypes, next2);
  }
  function toggleEdge(type) {
    const next2 = new Set(get(graphEdgeTypes));
    next2.has(type) ? next2.delete(type) : next2.add(type);
    set(graphEdgeTypes, next2);
  }
  function choosePreset(value) {
    set(graphPreset, value);
    set(graphLayout, value === "Evidence chain" ? "hierarchical" : value === "Entity network" ? "force" : "radial");
    set(graphNodeTypes, new Set(value === "Evidence chain" || value === "Full scoped graph" ? [
      "thread",
      "event",
      "entity",
      "location",
      "claim",
      "source",
      "question"
    ] : ["thread", "event", "entity", "location"]));
    set(depth, value === "Evidence chain" || value === "Full scoped graph" ? 3 : 1);
    set(selectedNode, "");
    set(expanded, /* @__PURE__ */ new Set());
  }
  function toggleSet(setter, value, set2) {
    const next2 = new Set(set2);
    next2.has(value) ? next2.delete(value) : next2.add(value);
    setter(next2);
  }
  function togglePin(id) {
    const next2 = new Set(get(pinned)), positions = new Map(get(pinnedPositions));
    if (next2.has(id)) {
      next2.delete(id);
      positions.delete(id);
    } else {
      const index2 = get(graphSlice).nodes.findIndex((node) => node.id === id);
      if (index2 < 0) return;
      positions.set(id, graphPosition(index2, get(graphSlice).nodes.length));
      next2.add(id);
    }
    set(pinned, next2);
    set(pinnedPositions, positions);
  }
  function hideNode(id) {
    set(hidden, /* @__PURE__ */ new Set([...get(hidden), id]));
    set(selectedNode, "");
    set(showInspector, false);
  }
  function filterLocation(id) {
    setScope("locationId", id);
    navigate("timeline");
  }
  function showLocation(id) {
    setScope("locationId", id);
    set(selectedLocation, id);
    set(selectedCluster, [id]);
    const location = repository().locationById.get(id);
    if (location) set(mapCenter, { lat: location.lat, lon: location.lon });
    navigate("map");
    set(showInspector, true);
  }
  function mapPick(group2) {
    set(selectedCluster, group2.locations.map((l) => l.location_id));
    set(selectedLocation, group2.locations[0].location_id);
    set(mapCenter, { lat: group2.lat, lon: group2.lon });
    set(showInspector, true);
  }
  function locationEvents(id) {
    const set2 = new Set(repository().locationById.get(id)?.event_ids || []);
    return repository().filteredEvents(get(scope)).filter((e) => set2.has(e.event_id));
  }
  function focusGraph(id) {
    set(selectedNode, id);
    update(graphRefresh);
    navigate("graph");
    set(showInspector, true);
  }
  function showEventMap(e) {
    if (!e.location_ids?.length) return;
    set(selectedLocation, e.location_ids[0]);
    set(selectedCluster, [get(selectedLocation)]);
    const location = repository().locationById.get(get(selectedLocation));
    if (location) set(mapCenter, { lat: location.lat, lon: location.lon });
    navigate("map");
    set(showInspector, true);
  }
  function openGraphNode(id) {
    const [type, object] = id.split(":");
    const node = repository().graphNode(id);
    if (type === "thread") navigate("thread", object);
    else if (type === "entity") navigate("entity", object);
    else if (type === "event") openEvent(repository().eventById.get(object));
    else if (type === "location") filterLocation(object);
    else if (type === "claim" && node?.owner_event_id) openEvent(repository().eventById.get(node?.owner_event_id));
    else if (type === "question" && node?.owner_thread_id) navigate("thread", node?.owner_thread_id);
    else if (type === "source" && /^https?:\/\//.test(node?.url || "")) window.open(node?.url, "_blank", "noopener,noreferrer");
  }
  function formatDate(value) {
    return value ? value.slice(0, 16).replace("T", " ") : "\u2014";
  }
  function groupedEvents(events, mode, start, limit) {
    const groups = /* @__PURE__ */ new Map();
    events.forEach((e, index2) => {
      const keys = mode === "thread" ? e.thread_ids.map(threadName) : mode === "entity" ? e.entity_ids.map(entityName) : [
        dateOf(e).slice(0, get(timeRange) === "All" || get(timeRange) === "1y" ? 7 : 10)
      ];
      for (const key2 of keys.length ? keys : ["\u672A\u5173\u8054"]) {
        if (!groups.has(key2)) groups.set(key2, { items: [], count: 0 });
        const bucket = groups.get(key2);
        bucket.count++;
        if (index2 >= start && index2 < start + limit) bucket.items.push(e);
      }
    });
    return [...groups.entries()].filter(([, bucket]) => bucket.items.length);
  }
  function isMonthly() {
    return get(group) === "date" && (get(timeRange) === "All" || get(timeRange) === "1y");
  }
  function periodOpen(name) {
    return periodStates.has(name) ? periodStates.get(name) : name === get(timelineGroups)[0]?.[0];
  }
  function togglePeriod(name) {
    const next2 = new Map(periodStates);
    next2.set(name, !periodOpen(name));
    periodStates = next2;
  }
  function timelinePage(start) {
    set(timelineStart, Math.max(0, Math.min(start, Math.max(0, get(visibleEvents).length - 1))));
    tick().then(() => {
      const pane = get(appRoot)?.querySelector(".wh-content");
      if (pane) pane.scrollTop = 0;
    });
  }
  function openThreadWeek(start) {
    const end = /* @__PURE__ */ new Date(start + "T00:00:00Z");
    end.setUTCDate(end.getUTCDate() + 6);
    set(scope, {
      ...get(scope),
      from: start,
      to: end.toISOString().slice(0, 10)
    });
    set(timeRange, "Custom");
    set(threadProjection, "Timeline");
  }
  function currentProjectionEvents() {
    return get(currentThread) ? (get(currentThread).event_summaries || []).filter((e) => repository().matchesEvent(e, get(scope))) : [];
  }
  let threadProjection = mutable_source("Overview");
  let entityProjection = mutable_source("Overview");
  legacy_pre_effect(() => (deep_read_state(repository()), get(page), get(scope)), () => {
    set(visibleThreads, repository() && get(page) === "threads" ? sortedThreads(repository().filteredThreads(get(scope))) : []);
  });
  legacy_pre_effect(() => (get(page), get(inspectorId), get(visibleThreads)), () => {
    set(homeThreadId, get(page) === "threads" ? get(inspectorId) && get(visibleThreads).some((t) => t.thread_id === get(inspectorId)) ? get(inspectorId) : get(visibleThreads)[0]?.thread_id : "");
  });
  legacy_pre_effect(() => (deep_read_state(repository()), get(homeThreadId)), () => {
    set(homeThread, repository() && get(homeThreadId) ? repository().thread(get(homeThreadId)) : null);
  });
  legacy_pre_effect(() => (deep_read_state(repository()), get(page), get(scope)), () => {
    set(observatoryEvents, repository() && get(page) === "threads" ? repository().filteredEvents({
      ...get(scope),
      from: [
        get(scope).from,
        new Date(Date.now() - 7 * 864e5).toISOString().slice(0, 10)
      ].sort().at(-1)
    }) : []);
  });
  legacy_pre_effect(() => get(visibleThreads), () => {
    set(attentionCount, get(visibleThreads).filter((t) => t.attention.required).length);
  });
  legacy_pre_effect(() => get(visibleThreads), () => {
    set(changedCount, get(visibleThreads).filter((t) => t.last_meaningful_change_at && Date.parse(t.last_meaningful_change_at) >= Date.now() - 7 * 864e5).length);
  });
  legacy_pre_effect(() => get(visibleThreads), () => {
    set(openQuestionCount, get(visibleThreads).reduce((sum, t) => sum + t.open_question_count, 0));
  });
  legacy_pre_effect(() => (deep_read_state(repository()), get(page), get(scope)), () => {
    set(visibleEvents, repository() && get(page) === "timeline" ? repository().filteredEvents(get(scope)) : []);
  });
  legacy_pre_effect(
    () => (get(page), get(visibleEvents), get(group), get(timelineStart)),
    () => {
      set(timelineGroups, get(page) === "timeline" ? groupedEvents(get(visibleEvents), get(group), get(timelineStart), timelineWindow) : []);
    }
  );
  legacy_pre_effect(
    () => (deep_read_state(repository()), get(page), get(scope), get(entityKind), get(minimumActivity)),
    () => {
      set(visibleEntities, repository() && get(page) === "entities" ? repository().filteredEntities(get(scope)).filter((e) => (!get(entityKind) || e.kind === get(entityKind)) && e.event_count >= get(minimumActivity)) : []);
    }
  );
  legacy_pre_effect(
    () => (deep_read_state(repository()), get(page), get(detailId)),
    () => {
      set(currentThread, repository() && get(page) === "thread" ? repository().thread(get(detailId)) : null);
    }
  );
  legacy_pre_effect(
    () => (deep_read_state(repository()), get(page), get(detailId)),
    () => {
      set(currentEntity, repository() && get(page) === "entity" ? repository().entity(get(detailId)) : null);
    }
  );
  legacy_pre_effect(
    () => (deep_read_state(repository()), get(page), get(scope), get(depth), get(maxNodes), get(selectedNode), get(graphNodeTypes), get(graphEdgeTypes), get(hidden), get(expanded), get(graphRefresh), get(graphPreset), get(localContext)),
    () => {
      set(graphSlice, repository() && get(page) === "graph" ? scopedGraph(get(scope), get(depth), get(maxNodes), get(selectedNode), get(graphNodeTypes), get(graphEdgeTypes), get(hidden), get(expanded), get(graphRefresh), get(graphPreset), get(localContext)) : { nodes: [], edges: [] });
    }
  );
  legacy_pre_effect(
    () => (get(graphSlice), get(graphLayout), get(pinnedPositions)),
    () => {
      set(graphPositions, layoutPositions(get(graphSlice), get(graphLayout), get(pinnedPositions)));
    }
  );
  legacy_pre_effect(
    () => (deep_read_state(repository()), get(page), get(threadProjection), get(entityProjection), get(scope), get(mapMode)),
    () => {
      set(locationPoints, repository() && (get(page) === "map" || get(page) === "thread" && get(threadProjection) === "Map" || get(page) === "entity" && get(entityProjection) === "Map") ? mapPoints(get(scope), get(mapMode)) : []);
    }
  );
  legacy_pre_effect(() => (get(locationPoints), get(zoom), get(mapCenter)), () => {
    set(markerClusters, clusters(visibleMapPoints(get(locationPoints), get(zoom), get(mapCenter)), get(zoom)));
  });
  legacy_pre_effect(() => get(scope), () => {
    set(scopeCount, Object.values(get(scope)).filter(Boolean).length);
  });
  legacy_pre_effect(
    () => (deep_read_state(repository()), get(inspectorId), get(page)),
    () => {
      set(inspectedEvent, repository() && get(inspectorId) && ["timeline", "thread"].includes(get(page)) ? repository().eventById.get(get(inspectorId)) : null);
    }
  );
  legacy_pre_effect(() => (deep_read_state(repository()), get(inspectorId)), () => {
    set(inspectedThread, repository() && get(inspectorId) && repository().threadById.has(get(inspectorId)) ? repository().thread(get(inspectorId)) : null);
  });
  legacy_pre_effect(() => (deep_read_state(repository()), get(inspectorId)), () => {
    set(inspectedEntity, repository() && get(inspectorId) && repository().entityById.has(get(inspectorId)) ? repository().entity(get(inspectorId)) : null);
  });
  legacy_pre_effect_reset();
  init();
  var div = root_114();
  event("keydown", $window, keyboard);
  var header = child(div);
  var nav_1 = sibling(child(header));
  each(nav_1, 5, () => navs, index, ($$anchor2, nav) => {
    var button = root5();
    let classes;
    var text2 = only_child(button, true);
    template_effect(() => {
      classes = set_class(button, 1, "", null, classes, {
        active: get(page) === get(nav) || get(page) === "thread" && get(nav) === "threads" || get(page) === "entity" && get(nav) === "entities"
      });
      set_text(text2, (get(nav), untrack(() => labels[get(nav)])));
    });
    event("click", button, () => navigate(get(nav)));
    append($$anchor2, button);
  });
  reset(nav_1);
  var div_1 = sibling(nav_1);
  var button_1 = child(div_1);
  var button_2 = sibling(button_1);
  var button_3 = sibling(button_2);
  var button_4 = sibling(button_3);
  reset(div_1);
  reset(header);
  var div_2 = sibling(header, 2);
  var div_3 = child(div_2);
  var input = child(div_3);
  remove_input_defaults(input);
  bind_this(input, ($$value) => set(searchInput, $$value), () => get(searchInput));
  var node_1 = sibling(input);
  {
    var consequent_1 = ($$anchor2) => {
      var div_4 = root_33();
      var node_2 = child(div_4);
      {
        var consequent = ($$anchor3) => {
          var div_5 = root_16();
          var text_1 = only_child(div_5, true);
          template_effect(() => set_text(text_1, get(searchError)));
          append($$anchor3, div_5);
        };
        if_block(node_2, ($$render) => {
          if (get(searchError)) $$render(consequent);
        });
      }
      var node_3 = sibling(node_2);
      each(node_3, 1, () => get(searchResults), index, ($$anchor3, hit) => {
        var button_5 = root_25();
        var span = child(button_5);
        var text_2 = only_child(span, true);
        var strong = sibling(span);
        var text_3 = only_child(strong, true);
        var small = sibling(strong);
        var text_4 = only_child(small, true);
        reset(button_5);
        template_effect(
          ($0) => {
            set_text(text_2, (get(hit), untrack(() => get(hit).type)));
            set_text(text_3, (get(hit), untrack(() => get(hit).label)));
            set_text(text_4, $0);
          },
          [
            () => (get(hit), untrack(() => get(hit).summary.slice(0, 90)))
          ]
        );
        event("mousedown", button_5, preventDefault(() => openSearchHit(get(hit))));
        append($$anchor3, button_5);
      });
      reset(div_4);
      append($$anchor2, div_4);
    };
    if_block(node_1, ($$render) => {
      if (get(searchFocused), get(searchResults), get(searchError), untrack(() => get(searchFocused) && (get(searchResults).length || get(searchError)))) $$render(consequent_1);
    });
  }
  reset(div_3);
  var button_6 = sibling(div_3);
  var text_5 = only_child(button_6);
  var span_1 = sibling(button_6);
  var text_6 = only_child(span_1);
  var button_7 = sibling(span_1);
  var small_1 = sibling(button_7);
  var text_7 = only_child(small_1, true);
  reset(div_2);
  var node_4 = sibling(div_2, 2);
  {
    var consequent_2 = ($$anchor2) => {
      var div_6 = root_53();
      var label = child(div_6);
      var input_1 = sibling(child(label));
      remove_input_defaults(input_1);
      reset(label);
      var label_1 = sibling(label);
      var input_2 = sibling(child(label_1));
      remove_input_defaults(input_2);
      reset(label_1);
      var label_2 = sibling(label_1);
      var select = sibling(child(label_2));
      var option = child(select);
      option.value = option.__value = "";
      var node_5 = sibling(option);
      each(node_5, 0, () => ["active", "watching", "dormant", "resolved", "archived"], index, ($$anchor3, s) => {
        var option_1 = root_43();
        var text_8 = only_child(option_1, true);
        var option_1_value = {};
        template_effect(() => {
          set_text(text_8, s);
          if (option_1_value !== (option_1_value = s)) {
            option_1.value = (option_1.__value = option_1_value) ?? "";
          }
        });
        append($$anchor3, option_1);
      });
      reset(select);
      var select_value;
      init_select(select);
      reset(label_2);
      var label_3 = sibling(label_2);
      var select_1 = sibling(child(label_3));
      var option_2 = child(select_1);
      option_2.value = option_2.__value = "";
      var node_6 = sibling(option_2);
      each(node_6, 0, () => ["high", "normal", "low"], index, ($$anchor3, p) => {
        var option_3 = root_43();
        var text_9 = only_child(option_3, true);
        var option_3_value = {};
        template_effect(() => {
          set_text(text_9, p);
          if (option_3_value !== (option_3_value = p)) {
            option_3.value = (option_3.__value = option_3_value) ?? "";
          }
        });
        append($$anchor3, option_3);
      });
      reset(select_1);
      var select_1_value;
      init_select(select_1);
      reset(label_3);
      var label_4 = sibling(label_3);
      var select_2 = sibling(child(label_4));
      var option_4 = child(select_2);
      option_4.value = option_4.__value = "";
      var node_7 = sibling(option_4);
      each(
        node_7,
        1,
        () => (deep_read_state(repository()), untrack(() => repository()?.threads || [])),
        index,
        ($$anchor3, t) => {
          var option_5 = root_43();
          var text_10 = only_child(option_5, true);
          var option_5_value = {};
          template_effect(() => {
            set_text(text_10, (get(t), untrack(() => get(t).title)));
            if (option_5_value !== (option_5_value = (get(t), untrack(() => get(t).thread_id)))) {
              option_5.value = (option_5.__value = option_5_value) ?? "";
            }
          });
          append($$anchor3, option_5);
        }
      );
      reset(select_2);
      var select_2_value;
      init_select(select_2);
      reset(label_4);
      var label_5 = sibling(label_4);
      var select_3 = sibling(child(label_5));
      var option_6 = child(select_3);
      option_6.value = option_6.__value = "";
      var node_8 = sibling(option_6);
      each(
        node_8,
        1,
        () => (deep_read_state(repository()), untrack(() => repository()?.entities || [])),
        index,
        ($$anchor3, e) => {
          var option_7 = root_43();
          var text_11 = only_child(option_7, true);
          var option_7_value = {};
          template_effect(() => {
            set_text(text_11, (get(e), untrack(() => get(e).name)));
            if (option_7_value !== (option_7_value = (get(e), untrack(() => get(e).entity_id)))) {
              option_7.value = (option_7.__value = option_7_value) ?? "";
            }
          });
          append($$anchor3, option_7);
        }
      );
      reset(select_3);
      var select_3_value;
      init_select(select_3);
      reset(label_5);
      var label_6 = sibling(label_5);
      var select_4 = sibling(child(label_6));
      var option_8 = child(select_4);
      option_8.value = option_8.__value = "";
      var node_9 = sibling(option_8);
      each(
        node_9,
        1,
        () => (deep_read_state(repository()), untrack(() => repository()?.locations || [])),
        index,
        ($$anchor3, l) => {
          var option_9 = root_43();
          var text_12 = only_child(option_9, true);
          var option_9_value = {};
          template_effect(() => {
            set_text(text_12, (get(l), untrack(() => get(l).name)));
            if (option_9_value !== (option_9_value = (get(l), untrack(() => get(l).location_id)))) {
              option_9.value = (option_9.__value = option_9_value) ?? "";
            }
          });
          append($$anchor3, option_9);
        }
      );
      reset(select_4);
      var select_4_value;
      init_select(select_4);
      reset(label_6);
      var label_7 = sibling(label_6);
      var select_5 = sibling(child(label_7));
      var option_10 = child(select_5);
      option_10.value = option_10.__value = "";
      var node_10 = sibling(option_10);
      each(node_10, 0, () => ["supported", "uncertain", "contested", "superseded"], index, ($$anchor3, s) => {
        var option_11 = root_43();
        var text_13 = only_child(option_11, true);
        var option_11_value = {};
        template_effect(() => {
          set_text(text_13, s);
          if (option_11_value !== (option_11_value = s)) {
            option_11.value = (option_11.__value = option_11_value) ?? "";
          }
        });
        append($$anchor3, option_11);
      });
      reset(select_5);
      var select_5_value;
      init_select(select_5);
      reset(label_7);
      reset(div_6);
      template_effect(() => {
        set_value(input_1, (get(scope), untrack(() => get(scope).from)));
        set_value(input_2, (get(scope), untrack(() => get(scope).to)));
        if (select_value !== (select_value = (get(scope), untrack(() => get(scope).status)))) {
          select.value = (select.__value = select_value) ?? "", select_option(select, select_value);
        }
        if (select_1_value !== (select_1_value = (get(scope), untrack(() => get(scope).priority)))) {
          select_1.value = (select_1.__value = select_1_value) ?? "", select_option(select_1, select_1_value);
        }
        if (select_2_value !== (select_2_value = (get(scope), untrack(() => get(scope).threadId)))) {
          select_2.value = (select_2.__value = select_2_value) ?? "", select_option(select_2, select_2_value);
        }
        if (select_3_value !== (select_3_value = (get(scope), untrack(() => get(scope).entityId)))) {
          select_3.value = (select_3.__value = select_3_value) ?? "", select_option(select_3, select_3_value);
        }
        if (select_4_value !== (select_4_value = (get(scope), untrack(() => get(scope).locationId)))) {
          select_4.value = (select_4.__value = select_4_value) ?? "", select_option(select_4, select_4_value);
        }
        if (select_5_value !== (select_5_value = (get(scope), untrack(() => get(scope).claimState)))) {
          select_5.value = (select_5.__value = select_5_value) ?? "", select_option(select_5, select_5_value);
        }
      });
      event("change", input_1, (e) => {
        set(timeRange, "Custom");
        setScope("from", e.currentTarget.value);
      });
      event("change", input_2, (e) => {
        set(timeRange, "Custom");
        setScope("to", e.currentTarget.value);
      });
      event("change", select, (e) => setScope("status", e.currentTarget.value));
      event("change", select_1, (e) => setScope("priority", e.currentTarget.value));
      event("change", select_2, (e) => setScope("threadId", e.currentTarget.value));
      event("change", select_3, (e) => setScope("entityId", e.currentTarget.value));
      event("change", select_4, (e) => setScope("locationId", e.currentTarget.value));
      event("change", select_5, (e) => setScope("claimState", e.currentTarget.value));
      append($$anchor2, div_6);
    };
    if_block(node_4, ($$render) => {
      if (get(showFilters)) $$render(consequent_2);
    });
  }
  var node_11 = sibling(node_4, 2);
  {
    var consequent_3 = ($$anchor2) => {
      var div_7 = root_63();
      var text_14 = child(div_7);
      var button_8 = sibling(text_14);
      var button_9 = sibling(button_8);
      reset(div_7);
      template_effect(() => set_text(text_14, `\u8BFB\u6A21\u578B\u4E0D\u53EF\u7528\uFF1A${error() ?? ""}`));
      event("click", button_8, function(...$$args) {
        refresh()?.apply(this, $$args);
      });
      event("click", button_9, function(...$$args) {
        settings()?.apply(this, $$args);
      });
      append($$anchor2, div_7);
    };
    var consequent_80 = ($$anchor2) => {
      var fragment = root_113();
      var node_12 = first_child(fragment);
      {
        var consequent_4 = ($$anchor3) => {
          var div_8 = root_73();
          var text_15 = child(div_8, true);
          var button_10 = sibling(text_15);
          reset(div_8);
          template_effect(() => set_text(text_15, (deep_read_state(repository()), untrack(() => repository().warning))));
          event("click", button_10, function(...$$args) {
            refresh()?.apply(this, $$args);
          });
          append($$anchor3, div_8);
        };
        if_block(node_12, ($$render) => {
          if (deep_read_state(repository()), untrack(() => repository().warning)) $$render(consequent_4);
        });
      }
      var node_13 = sibling(node_12, 2);
      {
        var consequent_5 = ($$anchor3) => {
          var div_9 = root_83();
          var button_11 = sibling(child(div_9));
          reset(div_9);
          event("click", button_11, function(...$$args) {
            refresh()?.apply(this, $$args);
          });
          append($$anchor3, div_9);
        };
        if_block(node_13, ($$render) => {
          if (stale()) $$render(consequent_5);
        });
      }
      var main = sibling(node_13, 2);
      var node_14 = child(main);
      {
        var consequent_13 = ($$anchor3) => {
          var fragment_1 = root_18();
          var aside = first_child(fragment_1);
          var node_15 = sibling(child(aside));
          each(
            node_15,
            0,
            () => [
              "Attention",
              "Active",
              "Watching",
              "Dormant",
              "Resolved",
              "Open Questions",
              "Stale",
              "Recently Changed"
            ],
            index,
            ($$anchor4, view) => {
              var button_12 = root_102();
              let classes_1;
              var text_16 = child(button_12, true);
              var node_16 = sibling(text_16);
              {
                var consequent_6 = ($$anchor5) => {
                  var span_2 = root_92();
                  var text_17 = only_child(span_2, true);
                  template_effect(($0) => set_text(text_17, $0), [
                    () => (deep_read_state(repository()), untrack(() => repository().threads.filter((t) => t.attention.required).length))
                  ]);
                  append($$anchor5, span_2);
                };
                if_block(node_16, ($$render) => {
                  if (view === "Attention") $$render(consequent_6);
                });
              }
              reset(button_12);
              template_effect(() => {
                classes_1 = set_class(button_12, 1, "", null, classes_1, { active: get(saved) === view });
                set_text(text_16, view);
              });
              event("click", button_12, () => applySaved(view));
              append($$anchor4, button_12);
            }
          );
          var p_1 = sibling(node_15);
          var text_18 = only_child(p_1);
          reset(aside);
          var section = sibling(aside, 2);
          var div_10 = child(section);
          var div_11 = child(div_10);
          var strong_1 = sibling(child(div_11));
          var text_19 = only_child(strong_1, true);
          next();
          reset(div_11);
          var div_12 = sibling(div_11);
          var strong_2 = sibling(child(div_12));
          var text_20 = only_child(strong_2, true);
          next();
          reset(div_12);
          var div_13 = sibling(div_12);
          var strong_3 = sibling(child(div_13));
          var text_21 = only_child(strong_3, true);
          next();
          reset(div_13);
          var div_14 = sibling(div_13);
          var strong_4 = sibling(child(div_14));
          var text_22 = only_child(strong_4, true);
          next();
          reset(div_14);
          reset(div_10);
          var div_15 = sibling(div_10, 2);
          var h2 = child(div_15);
          var small_2 = sibling(child(h2));
          var text_23 = only_child(small_2, true);
          reset(h2);
          var label_8 = sibling(h2);
          var select_6 = sibling(child(label_8));
          var option_12 = child(select_6);
          option_12.value = option_12.__value = "attention";
          var option_13 = sibling(option_12);
          option_13.value = option_13.__value = "change";
          var option_14 = sibling(option_13);
          option_14.value = option_14.__value = "priority";
          var option_15 = sibling(option_14);
          option_15.value = option_15.__value = "title";
          var option_16 = sibling(option_15);
          option_16.value = option_16.__value = "tracking";
          reset(select_6);
          init_select(select_6);
          reset(label_8);
          reset(div_15);
          var node_17 = sibling(div_15, 2);
          {
            var consequent_7 = ($$anchor4) => {
              var div_16 = root_112();
              var button_13 = sibling(child(div_16));
              reset(div_16);
              event("click", button_13, clearScope);
              append($$anchor4, div_16);
            };
            if_block(node_17, ($$render) => {
              if (get(visibleThreads), untrack(() => !get(visibleThreads).length)) $$render(consequent_7);
            });
          }
          var node_18 = sibling(node_17, 2);
          each(node_18, 1, () => get(visibleThreads), index, ($$anchor4, thread) => {
            var div_17 = root_17();
            let classes_2;
            var div_18 = child(div_17);
            var strong_5 = child(div_18);
            var text_24 = only_child(strong_5, true);
            var span_3 = sibling(strong_5);
            var text_25 = only_child(span_3, true);
            var span_4 = sibling(span_3);
            var text_26 = only_child(span_4, true);
            reset(div_18);
            var p_2 = sibling(div_18, 2);
            var text_27 = only_child(p_2, true);
            var div_19 = sibling(p_2, 2);
            var node_19 = child(div_19);
            ActivitySparkline(node_19, {
              get series() {
                return get(thread), untrack(() => get(thread).activity_series);
              }
            });
            var span_5 = sibling(node_19);
            var node_20 = child(span_5);
            {
              var consequent_8 = ($$anchor5) => {
                var span_6 = root_123();
                append($$anchor5, span_6);
              };
              var d_1 = user_derived(() => (get(thread), untrack(() => get(thread).recent_change_types?.includes("claim_corrected"))));
              if_block(node_20, ($$render) => {
                if (get(d_1)) $$render(consequent_8);
              });
            }
            var node_21 = sibling(node_20);
            {
              var consequent_9 = ($$anchor5) => {
                var span_7 = root_132();
                append($$anchor5, span_7);
              };
              var d_2 = user_derived(() => (get(thread), untrack(() => get(thread).recent_change_types?.includes("claim_contested"))));
              if_block(node_21, ($$render) => {
                if (get(d_2)) $$render(consequent_9);
              });
            }
            var node_22 = sibling(node_21);
            {
              var consequent_10 = ($$anchor5) => {
                var span_8 = root_142();
                append($$anchor5, span_8);
              };
              var d_3 = user_derived(() => (get(thread), untrack(() => get(thread).recent_change_types?.includes("claim_retracted"))));
              if_block(node_22, ($$render) => {
                if (get(d_3)) $$render(consequent_10);
              });
            }
            var node_23 = sibling(node_22);
            {
              var consequent_11 = ($$anchor5) => {
                var span_9 = root_152();
                var text_28 = only_child(span_9);
                template_effect(() => set_text(text_28, `\u25CB ${(get(thread), untrack(() => get(thread).open_question_count)) ?? ""} \u95EE\u9898`));
                append($$anchor5, span_9);
              };
              if_block(node_23, ($$render) => {
                if (get(thread), untrack(() => get(thread).open_question_count)) $$render(consequent_11);
              });
            }
            reset(span_5);
            reset(div_19);
            var node_24 = sibling(div_19, 2);
            {
              var consequent_12 = ($$anchor5) => {
                var div_20 = root_162();
                var text_29 = only_child(div_20, true);
                template_effect(($0) => set_text(text_29, $0), [
                  () => (get(thread), untrack(() => get(thread).attention.reasons.map((r) => reasons[r] || r).join("\uFF1B")))
                ]);
                append($$anchor5, div_20);
              };
              if_block(node_24, ($$render) => {
                if (get(thread), untrack(() => get(thread).attention.required)) $$render(consequent_12);
              });
            }
            var small_3 = sibling(node_24, 2);
            var text_30 = only_child(small_3);
            reset(div_17);
            template_effect(
              ($0, $1, $2) => {
                classes_2 = set_class(div_17, 1, "wh-row wh-motion-row", null, classes_2, { selected: get(homeThreadId) === get(thread).thread_id });
                set_text(text_24, (get(thread), untrack(() => get(thread).title)));
                set_text(text_25, (get(thread), untrack(() => get(thread).status)));
                set_text(text_26, (get(thread), untrack(() => get(thread).priority)));
                set_text(text_27, $0);
                set_text(text_30, `${$1 ?? ""} \xB7 ${$2 ?? ""}`);
              },
              [
                () => (get(thread), untrack(() => get(thread).latest_event_title || get(thread).latest_event_summary?.slice(0, 100) || "\u5C1A\u65E0 Event")),
                () => (get(thread), untrack(() => formatDate(get(thread).last_meaningful_change_at))),
                () => (get(thread), untrack(() => get(thread).top_entity_ids.slice(0, 3).map(entityName).join(" \xB7 ")))
              ]
            );
            event("keydown", div_17, (e) => e.key === "Enter" && set(inspectorId, get(thread).thread_id));
            event("click", div_17, () => {
              set(inspectorId, get(thread).thread_id);
              set(showInspector, true);
            });
            event("dblclick", div_17, () => navigate("thread", get(thread).thread_id));
            append($$anchor4, div_17);
          });
          reset(section);
          template_effect(() => {
            set_text(text_18, `${(get(visibleThreads), untrack(() => get(visibleThreads).length)) ?? ""} Threads`);
            set_text(text_19, get(attentionCount));
            set_text(text_20, (get(observatoryEvents), untrack(() => get(observatoryEvents).length)));
            set_text(text_21, get(changedCount));
            set_text(text_22, get(openQuestionCount));
            set_text(text_23, (get(visibleThreads), untrack(() => get(visibleThreads).length)));
          });
          bind_select_value(select_6, () => get(sort), ($$value) => set(sort, $$value));
          append($$anchor3, fragment_1);
        };
        var consequent_33 = ($$anchor3) => {
          var section_1 = root_51();
          var div_21 = child(section_1);
          var div_22 = child(div_21);
          var button_14 = child(div_22);
          var h2_1 = sibling(button_14);
          var text_31 = only_child(h2_1, true);
          var span_10 = sibling(h2_1);
          var text_32 = only_child(span_10, true);
          var span_11 = sibling(span_10);
          var text_33 = only_child(span_11, true);
          reset(div_22);
          var div_23 = sibling(div_22);
          var button_15 = child(div_23);
          var button_16 = sibling(button_15);
          reset(div_23);
          reset(div_21);
          var div_24 = sibling(div_21);
          var text_34 = only_child(div_24);
          var div_25 = sibling(div_24);
          each(div_25, 4, () => ["Overview", "Timeline", "Map", "Graph"], index, ($$anchor4, projection) => {
            var button_17 = root5();
            let classes_3;
            var text_35 = only_child(button_17, true);
            template_effect(() => {
              classes_3 = set_class(button_17, 1, "", null, classes_3, { active: get(threadProjection) === projection });
              set_text(text_35, projection);
            });
            event("click", button_17, () => set(threadProjection, projection));
            append($$anchor4, button_17);
          });
          reset(div_25);
          var node_25 = sibling(div_25, 2);
          {
            var consequent_20 = ($$anchor4) => {
              var fragment_2 = root_332();
              var section_2 = first_child(fragment_2);
              var node_26 = sibling(child(section_2));
              {
                var consequent_17 = ($$anchor5) => {
                  var fragment_3 = root_222();
                  var p_3 = first_child(fragment_3);
                  var text_36 = only_child(p_3, true);
                  var small_4 = sibling(p_3);
                  var text_37 = only_child(small_4);
                  var node_27 = sibling(small_4);
                  {
                    var consequent_14 = ($$anchor6) => {
                      var div_26 = root_19();
                      var node_28 = sibling(child(div_26));
                      each(
                        node_28,
                        1,
                        () => (get(currentThread), untrack(() => get(currentThread).current_state.source_refs)),
                        index,
                        ($$anchor7, ref) => {
                          var button_18 = root5();
                          var text_38 = only_child(button_18, true);
                          template_effect(() => set_text(text_38, get(ref)));
                          event("click", button_18, () => repository().eventById.has(get(ref)) ? openEvent(repository().eventById.get(get(ref))) : null);
                          append($$anchor7, button_18);
                        }
                      );
                      reset(div_26);
                      append($$anchor6, div_26);
                    };
                    if_block(node_27, ($$render) => {
                      if (get(currentThread), untrack(() => get(currentThread).current_state.source_refs?.length)) $$render(consequent_14);
                    });
                  }
                  var node_29 = sibling(node_27);
                  {
                    var consequent_15 = ($$anchor6) => {
                      var button_19 = root_20();
                      event("click", button_19, () => openCanonical()(get(currentThread).current_state.canonical_ref));
                      append($$anchor6, button_19);
                    };
                    if_block(node_29, ($$render) => {
                      if (get(currentThread), untrack(() => get(currentThread).current_state.canonical_ref)) $$render(consequent_15);
                    });
                  }
                  var node_30 = sibling(node_29);
                  {
                    var consequent_16 = ($$anchor6) => {
                      var div_27 = root_21();
                      append($$anchor6, div_27);
                    };
                    if_block(node_30, ($$render) => {
                      if (get(currentThread), untrack(() => get(currentThread).current_state.stale)) $$render(consequent_16);
                    });
                  }
                  template_effect(
                    ($0) => {
                      set_text(text_36, (get(currentThread), untrack(() => get(currentThread).current_state.text)));
                      set_text(text_37, `${(get(currentThread), untrack(() => get(currentThread).current_state.provenance)) ?? ""} \xB7 ${$0 ?? ""}${(get(currentThread), untrack(() => get(currentThread).current_state.revision ? ` \xB7 ${get(currentThread).current_state.revision}` : "")) ?? ""}`);
                    },
                    [
                      () => (get(currentThread), untrack(() => formatDate(get(currentThread).current_state.updated_at)))
                    ]
                  );
                  append($$anchor5, fragment_3);
                };
                var alternate = ($$anchor5) => {
                  var p_4 = root_232();
                  append($$anchor5, p_4);
                };
                if_block(node_26, ($$render) => {
                  if (get(currentThread), untrack(() => get(currentThread).current_state?.text)) $$render(consequent_17);
                  else $$render(alternate, -1);
                });
              }
              reset(section_2);
              var node_31 = sibling(section_2);
              {
                var consequent_18 = ($$anchor5) => {
                  var section_3 = root_252();
                  var node_32 = sibling(child(section_3));
                  each(
                    node_32,
                    1,
                    () => (get(currentThread), untrack(() => get(currentThread).annotations)),
                    index,
                    ($$anchor6, annotation) => {
                      var fragment_4 = root_242();
                      var p_5 = first_child(fragment_4);
                      var text_39 = only_child(p_5, true);
                      var small_5 = sibling(p_5);
                      var button_20 = sibling(child(small_5));
                      reset(small_5);
                      template_effect(() => set_text(text_39, (get(annotation), untrack(() => get(annotation).text))));
                      event("click", button_20, () => openNote()(get(annotation).canonical_ref.path));
                      append($$anchor6, fragment_4);
                    }
                  );
                  reset(section_3);
                  append($$anchor5, section_3);
                };
                if_block(node_31, ($$render) => {
                  if (get(currentThread), untrack(() => get(currentThread).annotations?.length)) $$render(consequent_18);
                });
              }
              var section_4 = sibling(node_31);
              var node_33 = sibling(child(section_4));
              ActivitySparkline(node_33, {
                get series() {
                  return get(currentThread), untrack(() => get(currentThread).activity_series);
                },
                width: 300,
                height: 64
              });
              var node_34 = sibling(node_33, 2);
              {
                let $0 = derived_safe_equal(() => untrack(currentProjectionEvents));
                ContextCharts(node_34, {
                  get series() {
                    return get(currentThread), untrack(() => get(currentThread).activity_series);
                  },
                  get events() {
                    return get($0);
                  },
                  openWeek: openThreadWeek
                });
              }
              reset(section_4);
              var section_5 = sibling(section_4);
              var h3 = child(section_5);
              var span_12 = sibling(child(h3));
              var text_40 = only_child(span_12, true);
              reset(h3);
              var node_35 = sibling(h3);
              each(
                node_35,
                1,
                () => (get(currentThread), untrack(() => get(currentThread).open_questions?.filter((q) => q.state === "open") || [])),
                index,
                ($$anchor5, q) => {
                  var div_28 = root_26();
                  var strong_6 = child(div_28);
                  var text_41 = only_child(strong_6, true);
                  var small_6 = sibling(strong_6);
                  var text_42 = child(small_6);
                  var button_21 = sibling(text_42);
                  reset(small_6);
                  reset(div_28);
                  template_effect(
                    ($0, $1) => {
                      set_text(text_41, (get(q), untrack(() => get(q).question)));
                      set_text(text_42, `${(get(q), untrack(() => get(q).state)) ?? ""} \xB7 ${$0 ?? ""} \xB7 \u66F4\u65B0 ${$1 ?? ""} `);
                    },
                    [
                      () => (get(q), untrack(() => formatDate(get(q).opened_at))),
                      () => (get(q), untrack(() => formatDate(get(q).last_updated_at)))
                    ]
                  );
                  event("click", button_21, () => openCanonical()(get(q).canonical_ref));
                  append($$anchor5, div_28);
                },
                ($$anchor5) => {
                  var p_6 = root_27();
                  append($$anchor5, p_6);
                }
              );
              var details = sibling(node_35);
              var node_36 = sibling(child(details));
              each(
                node_36,
                1,
                () => (get(currentThread), untrack(() => get(currentThread).open_questions?.filter((q) => q.state !== "open") || [])),
                index,
                ($$anchor5, q) => {
                  var div_29 = root_29();
                  var text_43 = child(div_29);
                  var node_37 = sibling(text_43);
                  {
                    var consequent_19 = ($$anchor6) => {
                      var button_22 = root_28();
                      event("click", button_22, () => openEvent(repository().eventById.get(get(q).answer_event_id)));
                      append($$anchor6, button_22);
                    };
                    var d_4 = user_derived(() => (get(q), deep_read_state(repository()), untrack(() => get(q).answer_event_id && repository().eventById.has(get(q).answer_event_id))));
                    if_block(node_37, ($$render) => {
                      if (get(d_4)) $$render(consequent_19);
                    });
                  }
                  reset(div_29);
                  template_effect(() => set_text(text_43, `${(get(q), untrack(() => get(q).question)) ?? ""} \xB7 ${(get(q), untrack(() => get(q).state)) ?? ""}`));
                  append($$anchor5, div_29);
                }
              );
              reset(details);
              reset(section_5);
              var section_6 = sibling(section_5);
              var div_30 = sibling(child(section_6));
              each(
                div_30,
                5,
                () => (get(currentThread), untrack(() => get(currentThread).entity_ids || [])),
                index,
                ($$anchor5, id) => {
                  var button_23 = root5();
                  var text_44 = only_child(button_23, true);
                  template_effect(($0) => set_text(text_44, $0), [() => (get(id), untrack(() => entityName(get(id))))]);
                  event("click", button_23, () => navigate("entity", get(id)));
                  append($$anchor5, button_23);
                }
              );
              reset(div_30);
              reset(section_6);
              var section_7 = sibling(section_6);
              var node_38 = sibling(child(section_7));
              each(
                node_38,
                1,
                () => (get(currentThread), untrack(() => get(currentThread).related_threads || [])),
                index,
                ($$anchor5, rel) => {
                  var div_31 = root_30();
                  var button_24 = child(div_31);
                  var text_45 = only_child(button_24, true);
                  var small_7 = sibling(button_24);
                  var text_46 = only_child(small_7, true);
                  reset(div_31);
                  template_effect(
                    ($0) => {
                      set_text(text_45, $0);
                      set_text(text_46, (get(rel), untrack(() => get(rel).type)));
                    },
                    [
                      () => (get(rel), untrack(() => threadName(get(rel).thread_id)))
                    ]
                  );
                  event("click", button_24, () => navigate("thread", get(rel).thread_id));
                  append($$anchor5, div_31);
                },
                ($$anchor5) => {
                  var p_7 = root_31();
                  append($$anchor5, p_7);
                }
              );
              reset(section_7);
              var section_8 = sibling(section_7);
              var node_39 = sibling(child(section_8));
              each(node_39, 1, () => untrack(() => currentProjectionEvents().slice(0, 8)), index, ($$anchor5, e) => {
                var button_25 = root_322();
                var text_47 = only_child(button_25);
                template_effect(($0) => set_text(text_47, `${$0 ?? ""} \xB7 ${(get(e), untrack(() => get(e).title)) ?? ""}`), [() => (get(e), untrack(() => dateLabel(get(e))))]);
                event("click", button_25, () => {
                  set(threadProjection, "Timeline");
                  set(eventId, get(e).event_id);
                });
                append($$anchor5, button_25);
              });
              reset(section_8);
              template_effect(($0) => set_text(text_40, $0), [
                () => (get(currentThread), untrack(() => get(currentThread).open_questions?.filter((q) => q.state === "open").length || 0))
              ]);
              append($$anchor4, fragment_2);
            };
            var consequent_30 = ($$anchor4) => {
              var fragment_5 = root_46();
              var node_40 = first_child(fragment_5);
              each(
                node_40,
                1,
                () => (get(threadEventLimit), untrack(() => currentProjectionEvents().slice(0, get(threadEventLimit)))),
                index,
                ($$anchor5, e) => {
                  var div_32 = root_432();
                  let classes_4;
                  var span_13 = child(div_32);
                  let classes_5;
                  var div_33 = sibling(span_13);
                  var button_26 = child(div_33);
                  var text_48 = only_child(button_26, true);
                  var node_41 = sibling(button_26);
                  {
                    var consequent_21 = ($$anchor6) => {
                      var span_14 = root_34();
                      append($$anchor6, span_14);
                    };
                    if_block(node_41, ($$render) => {
                      if (get(e), untrack(() => get(e).has_corrected_claim)) $$render(consequent_21);
                    });
                  }
                  var node_42 = sibling(node_41);
                  {
                    var consequent_22 = ($$anchor6) => {
                      var span_15 = root_35();
                      append($$anchor6, span_15);
                    };
                    if_block(node_42, ($$render) => {
                      if (get(e), untrack(() => get(e).has_contested_claim)) $$render(consequent_22);
                    });
                  }
                  var small_8 = sibling(node_42);
                  var text_49 = only_child(small_8);
                  reset(div_33);
                  var p_8 = sibling(div_33);
                  var text_50 = only_child(p_8, true);
                  var details_1 = sibling(p_8);
                  var div_34 = sibling(child(details_1));
                  var text_51 = only_child(div_34);
                  var div_35 = sibling(div_34);
                  var node_43 = child(div_35);
                  each(node_43, 1, () => (get(e), untrack(() => get(e).entity_ids)), index, ($$anchor6, id) => {
                    var button_27 = root5();
                    var text_52 = only_child(button_27, true);
                    template_effect(($0) => set_text(text_52, $0), [() => (get(id), untrack(() => entityName(get(id))))]);
                    event("click", button_27, () => navigate("entity", get(id)));
                    append($$anchor6, button_27);
                  });
                  var node_44 = sibling(node_43);
                  each(node_44, 1, () => (get(e), untrack(() => get(e).location_ids)), index, ($$anchor6, id) => {
                    var button_28 = root5();
                    var text_53 = only_child(button_28, true);
                    template_effect(($0) => set_text(text_53, $0), [
                      () => (deep_read_state(repository()), get(id), untrack(() => repository().locationById.get(get(id))?.name || get(id)))
                    ]);
                    event("click", button_28, () => filterLocation(get(id)));
                    append($$anchor6, button_28);
                  });
                  reset(div_35);
                  var small_9 = sibling(div_35);
                  var text_54 = only_child(small_9);
                  var button_29 = sibling(small_9);
                  var node_45 = sibling(button_29);
                  {
                    var consequent_23 = ($$anchor6) => {
                      var button_30 = root_36();
                      event("click", button_30, () => openRef(get(e).canonical_ref));
                      append($$anchor6, button_30);
                    };
                    if_block(node_45, ($$render) => {
                      if (get(e), untrack(() => get(e).canonical_ref.obsidian_path)) $$render(consequent_23);
                    });
                  }
                  var node_46 = sibling(node_45);
                  {
                    var consequent_27 = ($$anchor6) => {
                      var fragment_6 = comment();
                      var node_47 = first_child(fragment_6);
                      each(
                        node_47,
                        1,
                        () => (deep_read_state(repository()), get(e), untrack(() => repository().event(get(e).event_id).claims || [])),
                        index,
                        ($$anchor7, claim) => {
                          var div_36 = root_40();
                          var strong_7 = child(div_36);
                          var text_55 = only_child(strong_7);
                          var text_56 = sibling(strong_7);
                          var node_48 = sibling(text_56);
                          {
                            var consequent_24 = ($$anchor8) => {
                              var small_10 = root_37();
                              var text_57 = only_child(small_10);
                              template_effect(() => set_text(text_57, `\u88AB Claim ${(get(claim), untrack(() => get(claim).superseded_by)) ?? ""} \u53D6\u4EE3`));
                              append($$anchor8, small_10);
                            };
                            if_block(node_48, ($$render) => {
                              if (get(claim), untrack(() => get(claim).superseded_by)) $$render(consequent_24);
                            });
                          }
                          var button_31 = sibling(node_48);
                          var small_11 = sibling(button_31);
                          var text_58 = child(small_11);
                          var node_49 = sibling(text_58);
                          {
                            var consequent_25 = ($$anchor8) => {
                              var button_32 = root_38();
                              event("click", button_32, () => openCanonical()(get(claim).source.canonical_ref));
                              append($$anchor8, button_32);
                            };
                            if_block(node_49, ($$render) => {
                              if (get(claim), untrack(() => get(claim).source)) $$render(consequent_25);
                            });
                          }
                          var node_50 = sibling(node_49, 2);
                          {
                            var consequent_26 = ($$anchor8) => {
                              var a_1 = root_39();
                              template_effect(() => set_attribute2(a_1, "href", (get(claim), untrack(() => get(claim).source.url))));
                              append($$anchor8, a_1);
                            };
                            if_block(node_50, ($$render) => {
                              if (get(claim), untrack(() => get(claim).source?.url)) $$render(consequent_26);
                            });
                          }
                          reset(small_11);
                          reset(div_36);
                          template_effect(() => {
                            set_text(text_55, `${(get(claim), untrack(() => stateGlyph[get(claim).state] || "\u25B3")) ?? ""} ${(get(claim), untrack(() => get(claim).state)) ?? ""}`);
                            set_text(text_56, ` ${(get(claim), untrack(() => get(claim).statement)) ?? ""}`);
                            set_text(text_58, `${(get(claim), untrack(() => get(claim).source?.publisher || "\u6765\u6E90\u672A\u77E5")) ?? ""} \xB7 ${(get(claim), untrack(() => get(claim).source?.title || "\u6765\u6E90\u7F3A\u5931")) ?? ""} \xB7 ${(get(claim), untrack(() => get(claim).source?.source_kind || "unknown")) ?? ""} \xB7 ${(get(claim), untrack(() => get(claim).source?.published_at || "\u65E5\u671F\u672A\u77E5")) ?? ""} \xB7 ${(get(claim), untrack(() => get(claim).source?.relationship || "\u6765\u6E90")) ?? ""} `);
                          });
                          event("click", button_31, () => openCanonical()(get(claim).canonical_ref));
                          append($$anchor7, div_36);
                        }
                      );
                      append($$anchor6, fragment_6);
                    };
                    var d_5 = user_derived(() => (get(expandedEvents), get(e), untrack(() => get(expandedEvents).has(get(e).event_id))));
                    if_block(node_46, ($$render) => {
                      if (get(d_5)) $$render(consequent_27);
                    });
                  }
                  var node_51 = sibling(node_46);
                  {
                    var consequent_28 = ($$anchor6) => {
                      var fragment_7 = root_422();
                      var node_52 = sibling(first_child(fragment_7));
                      each(
                        node_52,
                        1,
                        () => (get(currentThread), untrack(() => get(currentThread).annotations)),
                        index,
                        ($$anchor7, annotation) => {
                          var div_37 = root_41();
                          var text_59 = child(div_37, true);
                          var button_33 = sibling(text_59);
                          reset(div_37);
                          template_effect(() => set_text(text_59, (get(annotation), untrack(() => get(annotation).text))));
                          event("click", button_33, () => openNote()(get(annotation).canonical_ref.path));
                          append($$anchor7, div_37);
                        }
                      );
                      append($$anchor6, fragment_7);
                    };
                    if_block(node_51, ($$render) => {
                      if (get(currentThread), untrack(() => get(currentThread).annotations?.length)) $$render(consequent_28);
                    });
                  }
                  reset(details_1);
                  reset(div_32);
                  template_effect(
                    ($0, $1) => {
                      classes_4 = set_class(div_32, 1, "wh-event-card", null, classes_4, { highlight: get(eventId) === get(e).event_id });
                      classes_5 = set_class(span_13, 1, "wh-detail-time-node", null, classes_5, {
                        approximate: get(e).time_precision !== "day",
                        corrected: get(e).has_corrected_claim,
                        contested: get(e).has_contested_claim
                      });
                      set_attribute2(span_13, "title", $0);
                      set_text(text_48, (get(e), untrack(() => get(e).title)));
                      set_text(text_49, `${$1 ?? ""} \xB7 ${(get(e), untrack(() => get(e).claim_count)) ?? ""} Claims \xB7 ${(get(e), untrack(() => get(e).source_count)) ?? ""} Sources`);
                      set_text(text_50, (get(e), untrack(() => get(e).summary)));
                      details_1.open = (get(eventId), get(e), untrack(() => get(eventId) === get(e).event_id));
                      set_text(text_51, `\u53D1\u751F ${(get(e), untrack(() => get(e).occurred_at || "\u672A\u77E5")) ?? ""}\uFF08${(get(e), untrack(() => get(e).time_precision)) ?? ""}\uFF09 \xB7 \u62A5\u9053 ${(get(e), untrack(() => get(e).reported_at || "\u2014")) ?? ""} \xB7 \u9996\u6B21\u89C2\u5BDF ${(get(e), untrack(() => get(e).first_observed_at || "\u2014")) ?? ""} \xB7 \u7F6E\u4FE1\u5EA6 ${(get(e), untrack(() => get(e).confidence)) ?? ""} \xB7 \u72B6\u6001 ${(get(e), untrack(() => get(e).state)) ?? ""}`);
                      set_text(text_54, `Chronicle: ${(get(e), untrack(() => get(e).event_id)) ?? ""}`);
                    },
                    [
                      () => (get(e), untrack(() => dateLabel(get(e)))),
                      () => (get(e), untrack(() => dateLabel(get(e))))
                    ]
                  );
                  event("click", button_26, () => inspectEvent(get(e).event_id));
                  event("click", button_29, () => openCanonical()(get(e).canonical_ref));
                  event("toggle", details_1, (ev) => toggleEventDetail(get(e).event_id, ev.currentTarget.open));
                  append($$anchor5, div_32);
                },
                ($$anchor5) => {
                  var div_38 = root_44();
                  var button_34 = sibling(child(div_38));
                  reset(div_38);
                  event("click", button_34, clearScope);
                  append($$anchor5, div_38);
                }
              );
              var node_53 = sibling(node_40);
              {
                var consequent_29 = ($$anchor5) => {
                  var button_35 = root_45();
                  event("click", button_35, () => set(threadEventLimit, get(threadEventLimit) + 100));
                  append($$anchor5, button_35);
                };
                var d_6 = user_derived(() => (get(threadEventLimit), untrack(() => currentProjectionEvents().length > get(threadEventLimit))));
                if_block(node_53, ($$render) => {
                  if (get(d_6)) $$render(consequent_29);
                });
              }
              append($$anchor4, fragment_5);
            };
            var consequent_32 = ($$anchor4) => {
              const localPoints = derived_safe_equal(() => (get(locationPoints), get(currentThread), untrack(() => get(locationPoints).filter((l) => l.thread_ids.includes(get(currentThread).thread_id)))));
              var div_39 = root_49();
              var node_54 = sibling(child(div_39));
              ThreadProjection(node_54, {
                get thread() {
                  return get(currentThread);
                },
                get repository() {
                  return repository();
                },
                get scope() {
                  return get(scope);
                },
                projection: "Map",
                openLocation: showLocation
              });
              var node_55 = sibling(node_54);
              {
                var consequent_31 = ($$anchor5) => {
                  var div_40 = root_47();
                  each(div_40, 5, () => get(localPoints), index, ($$anchor6, l) => {
                    var button_36 = root5();
                    var text_60 = only_child(button_36);
                    template_effect(() => set_text(text_60, `${(get(l), untrack(() => get(l).name)) ?? ""} \xB7 ${(get(l), untrack(() => get(l).geo_precision)) ?? ""} \xB7 ${(get(l), untrack(() => get(l).count)) ?? ""} Events`));
                    event("click", button_36, () => {
                      set(selectedLocation, get(l).location_id);
                      set(selectedCluster, [get(l).location_id]);
                      set(showInspector, true);
                    });
                    append($$anchor6, button_36);
                  });
                  reset(div_40);
                  append($$anchor5, div_40);
                };
                var alternate_1 = ($$anchor5) => {
                  var div_41 = root_48();
                  append($$anchor5, div_41);
                };
                if_block(node_55, ($$render) => {
                  if (deep_read_state(get(localPoints)), untrack(() => get(localPoints).length)) $$render(consequent_31);
                  else $$render(alternate_1, -1);
                });
              }
              reset(div_39);
              append($$anchor4, div_39);
            };
            var alternate_2 = ($$anchor4) => {
              var div_42 = root_50();
              var node_56 = sibling(child(div_42));
              ThreadProjection(node_56, {
                get thread() {
                  return get(currentThread);
                },
                get repository() {
                  return repository();
                },
                get scope() {
                  return get(scope);
                },
                projection: "Graph",
                openEntity: (id) => navigate("entity", id)
              });
              var button_37 = sibling(node_56);
              next();
              reset(div_42);
              event("click", button_37, () => {
                navigate("graph", "", {
                  localContext: { type: "thread", id: get(currentThread).thread_id }
                });
              });
              append($$anchor4, div_42);
            };
            if_block(node_25, ($$render) => {
              if (get(threadProjection) === "Overview") $$render(consequent_20);
              else if (get(threadProjection) === "Timeline") $$render(consequent_30, 1);
              else if (get(threadProjection) === "Map") $$render(consequent_32, 2);
              else $$render(alternate_2, -1);
            });
          }
          reset(section_1);
          template_effect(
            ($0, $1) => {
              set_text(text_31, (get(currentThread), untrack(() => get(currentThread).title)));
              set_text(text_32, (get(currentThread), untrack(() => get(currentThread).status)));
              set_text(text_33, (get(currentThread), untrack(() => get(currentThread).priority)));
              button_15.disabled = (get(currentThread), untrack(() => !get(currentThread).canonical_ref.obsidian_path));
              set_text(text_34, `\u8DDF\u8E2A\u81EA ${$0 ?? ""} \xB7 \u6700\u8FD1\u6709\u610F\u4E49\u53D8\u66F4 ${$1 ?? ""} \xB7 Chronicle ID ${(get(currentThread), untrack(() => get(currentThread).thread_id)) ?? ""}`);
            },
            [
              () => (get(currentThread), untrack(() => formatDate(get(currentThread).tracking_since))),
              () => (get(currentThread), untrack(() => formatDate(get(currentThread).last_meaningful_change_at)))
            ]
          );
          event("click", button_14, back);
          event("click", button_15, () => openRef(get(currentThread).canonical_ref));
          event("click", button_16, () => openCanonical()(get(currentThread).canonical_ref));
          append($$anchor3, section_1);
        };
        var consequent_45 = ($$anchor3) => {
          var section_9 = root_64();
          var div_43 = child(section_9);
          var h2_2 = child(div_43);
          var small_12 = sibling(child(h2_2));
          var text_61 = only_child(small_12);
          reset(h2_2);
          var div_44 = sibling(h2_2);
          var div_45 = child(div_44);
          each(div_45, 4, () => ["7d", "30d", "90d", "1y", "All", "Custom"], index, ($$anchor4, range) => {
            var button_38 = root5();
            let classes_6;
            var text_62 = only_child(button_38, true);
            template_effect(() => {
              classes_6 = set_class(button_38, 1, "", null, classes_6, { active: get(timeRange) === range });
              set_text(text_62, range);
            });
            event("click", button_38, () => setTimeRange(range));
            append($$anchor4, button_38);
          });
          reset(div_45);
          var label_9 = sibling(div_45);
          var select_7 = sibling(child(label_9));
          var option_17 = child(select_7);
          option_17.value = option_17.__value = "date";
          var option_18 = sibling(option_17);
          option_18.value = option_18.__value = "thread";
          var option_19 = sibling(option_18);
          option_19.value = option_19.__value = "entity";
          reset(select_7);
          init_select(select_7);
          reset(label_9);
          var label_10 = sibling(label_9);
          var select_8 = sibling(child(label_10));
          var option_20 = child(select_8);
          option_20.value = option_20.__value = "normal";
          var option_21 = sibling(option_20);
          option_21.value = option_21.__value = "compact";
          reset(select_8);
          init_select(select_8);
          reset(label_10);
          reset(div_44);
          reset(div_43);
          var node_57 = sibling(div_43);
          {
            var consequent_34 = ($$anchor4) => {
              var div_46 = root_44();
              var button_39 = sibling(child(div_46));
              reset(div_46);
              event("click", button_39, clearScope);
              append($$anchor4, div_46);
            };
            if_block(node_57, ($$render) => {
              if (get(visibleEvents), untrack(() => !get(visibleEvents).length)) $$render(consequent_34);
            });
          }
          var node_58 = sibling(node_57);
          each(node_58, 1, () => get(timelineGroups), index, ($$anchor4, $$item) => {
            var $$array = user_derived(() => to_array(get($$item), 2));
            let name = () => get($$array)[0];
            let bucket = () => get($$array)[1];
            var fragment_8 = root_622();
            var h3_1 = first_child(fragment_8);
            var node_59 = child(h3_1);
            {
              var consequent_35 = ($$anchor5) => {
                var button_40 = root_522();
                var text_63 = only_child(button_40);
                template_effect(
                  ($0, $1) => {
                    set_attribute2(button_40, "aria-expanded", $0);
                    set_text(text_63, `${$1 ?? ""} ${name() ?? ""}`);
                  },
                  [
                    () => (name(), untrack(() => periodOpen(name()))),
                    () => (name(), untrack(() => periodOpen(name()) ? "\u25BE" : "\u25B8"))
                  ]
                );
                event("click", button_40, () => togglePeriod(name()));
                append($$anchor5, button_40);
              };
              var d_7 = user_derived(() => untrack(isMonthly));
              var alternate_3 = ($$anchor5) => {
                var text_64 = text();
                template_effect(() => set_text(text_64, name()));
                append($$anchor5, text_64);
              };
              if_block(node_59, ($$render) => {
                if (get(d_7)) $$render(consequent_35);
                else $$render(alternate_3, -1);
              });
            }
            var span_16 = sibling(node_59, 2);
            var small_13 = sibling(span_16);
            var text_65 = only_child(small_13);
            reset(h3_1);
            var node_60 = sibling(h3_1);
            {
              var consequent_43 = ($$anchor5) => {
                var fragment_10 = comment();
                var node_61 = first_child(fragment_10);
                each(node_61, 1, () => (bucket(), untrack(() => bucket().items)), index, ($$anchor6, e) => {
                  var div_47 = root_61();
                  let classes_7;
                  var div_48 = child(div_47);
                  var span_17 = child(div_48);
                  let classes_8;
                  var text_66 = sibling(span_17, 1, true);
                  reset(div_48);
                  var div_49 = sibling(div_48);
                  var strong_8 = child(div_49);
                  var text_67 = only_child(strong_8, true);
                  var node_62 = sibling(strong_8);
                  {
                    var consequent_36 = ($$anchor7) => {
                      var span_18 = root_532();
                      append($$anchor7, span_18);
                    };
                    if_block(node_62, ($$render) => {
                      if (get(e), untrack(() => get(e).has_corrected_claim)) $$render(consequent_36);
                    });
                  }
                  var node_63 = sibling(node_62);
                  {
                    var consequent_37 = ($$anchor7) => {
                      var span_19 = root_54();
                      append($$anchor7, span_19);
                    };
                    if_block(node_63, ($$render) => {
                      if (get(e), untrack(() => get(e).has_contested_claim)) $$render(consequent_37);
                    });
                  }
                  var small_14 = sibling(node_63);
                  var text_68 = only_child(small_14, true);
                  var node_64 = sibling(small_14);
                  {
                    var consequent_38 = ($$anchor7) => {
                      var p_9 = root_55();
                      var text_69 = only_child(p_9, true);
                      template_effect(() => set_text(text_69, (get(e), untrack(() => get(e).summary))));
                      append($$anchor7, p_9);
                    };
                    if_block(node_64, ($$render) => {
                      if (get(density) !== "compact") $$render(consequent_38);
                    });
                  }
                  var small_15 = sibling(node_64);
                  var text_70 = only_child(small_15);
                  reset(div_49);
                  var button_41 = sibling(div_49);
                  var node_65 = sibling(button_41);
                  {
                    var consequent_42 = ($$anchor7) => {
                      const detail = derived_safe_equal(() => (deep_read_state(repository()), get(e), untrack(() => repository().event(get(e).event_id))));
                      var div_50 = root_60();
                      var div_51 = child(div_50);
                      var text_71 = only_child(div_51);
                      var p_10 = sibling(div_51, 2);
                      var text_72 = only_child(p_10, true);
                      var div_52 = sibling(p_10);
                      var node_66 = child(div_52);
                      each(node_66, 1, () => (get(e), untrack(() => get(e).entity_ids)), index, ($$anchor8, id) => {
                        var button_42 = root5();
                        var text_73 = only_child(button_42, true);
                        template_effect(($0) => set_text(text_73, $0), [() => (get(id), untrack(() => entityName(get(id))))]);
                        event("click", button_42, () => navigate("entity", get(id)));
                        append($$anchor8, button_42);
                      });
                      var node_67 = sibling(node_66);
                      each(node_67, 1, () => (get(e), untrack(() => get(e).location_ids)), index, ($$anchor8, id) => {
                        var button_43 = root5();
                        var text_74 = only_child(button_43, true);
                        template_effect(($0) => set_text(text_74, $0), [
                          () => (deep_read_state(repository()), get(id), untrack(() => repository().locationById.get(get(id))?.name || get(id)))
                        ]);
                        event("click", button_43, () => showLocation(get(id)));
                        append($$anchor8, button_43);
                      });
                      reset(div_52);
                      var node_68 = sibling(div_52, 2);
                      each(
                        node_68,
                        1,
                        () => (deep_read_state(get(detail)), untrack(() => get(detail).claims || [])),
                        index,
                        ($$anchor8, claim) => {
                          var div_53 = root_57();
                          var strong_9 = child(div_53);
                          var text_75 = only_child(strong_9);
                          var text_76 = sibling(strong_9);
                          var small_16 = sibling(text_76);
                          var text_77 = child(small_16);
                          var node_69 = sibling(text_77);
                          {
                            var consequent_39 = ($$anchor9) => {
                              var a_2 = root_56();
                              template_effect(() => set_attribute2(a_2, "href", (get(claim), untrack(() => get(claim).source.url))));
                              append($$anchor9, a_2);
                            };
                            if_block(node_69, ($$render) => {
                              if (get(claim), untrack(() => get(claim).source?.url)) $$render(consequent_39);
                            });
                          }
                          reset(small_16);
                          var button_44 = sibling(small_16);
                          reset(div_53);
                          template_effect(() => {
                            set_text(text_75, `${(get(claim), untrack(() => stateGlyph[get(claim).state] || "\u25B3")) ?? ""} ${(get(claim), untrack(() => get(claim).state)) ?? ""}`);
                            set_text(text_76, ` ${(get(claim), untrack(() => get(claim).statement)) ?? ""}`);
                            set_text(text_77, `${(get(claim), untrack(() => get(claim).source?.publisher || "\u6765\u6E90\u672A\u77E5")) ?? ""} \xB7 ${(get(claim), untrack(() => get(claim).source?.title || "\u6765\u6E90\u7F3A\u5931")) ?? ""} `);
                          });
                          event("click", button_44, () => openCanonical()(get(claim).canonical_ref));
                          append($$anchor8, div_53);
                        }
                      );
                      var node_70 = sibling(node_68, 2);
                      each(node_70, 1, () => (get(e), untrack(() => get(e).thread_ids)), index, ($$anchor8, ownerId) => {
                        const owner = derived_safe_equal(() => (deep_read_state(repository()), get(ownerId), untrack(() => repository().thread(get(ownerId)))));
                        var fragment_11 = comment();
                        var node_71 = first_child(fragment_11);
                        {
                          var consequent_40 = ($$anchor9) => {
                            var fragment_12 = root_58();
                            var div_54 = first_child(fragment_12);
                            var text_78 = only_child(div_54);
                            var node_72 = sibling(div_54);
                            each(
                              node_72,
                              1,
                              () => (deep_read_state(get(owner)), untrack(() => get(owner).annotations)),
                              index,
                              ($$anchor10, annotation) => {
                                var div_55 = root_41();
                                var text_79 = child(div_55, true);
                                var button_45 = sibling(text_79);
                                reset(div_55);
                                template_effect(() => set_text(text_79, (get(annotation), untrack(() => get(annotation).text))));
                                event("click", button_45, () => openNote()(get(annotation).canonical_ref.path));
                                append($$anchor10, div_55);
                              }
                            );
                            template_effect(() => set_text(text_78, `\u270E ${(deep_read_state(get(owner)), untrack(() => get(owner).title)) ?? ""} \u7684\u4EBA\u5DE5\u6279\u6CE8\uFF08Thread \u7EA7\u4E0A\u4E0B\u6587\uFF09`));
                            append($$anchor9, fragment_12);
                          };
                          if_block(node_71, ($$render) => {
                            if (deep_read_state(get(owner)), untrack(() => get(owner).annotations?.length)) $$render(consequent_40);
                          });
                        }
                        append($$anchor8, fragment_11);
                      });
                      var div_56 = sibling(node_70);
                      var button_46 = child(div_56);
                      var button_47 = sibling(button_46);
                      var node_73 = sibling(button_47);
                      {
                        var consequent_41 = ($$anchor8) => {
                          var button_48 = root_59();
                          event("click", button_48, () => showEventMap(get(e)));
                          append($$anchor8, button_48);
                        };
                        if_block(node_73, ($$render) => {
                          if (get(e), untrack(() => get(e).location_ids.length)) $$render(consequent_41);
                        });
                      }
                      reset(div_56);
                      reset(div_50);
                      template_effect(() => {
                        set_text(text_71, `\u53D1\u751F ${(get(e), untrack(() => get(e).occurred_at || "\u672A\u77E5")) ?? ""}\uFF08${(get(e), untrack(() => get(e).time_precision)) ?? ""}\uFF09 \xB7 \u62A5\u9053 ${(get(e), untrack(() => get(e).reported_at || "\u2014")) ?? ""} \xB7 \u9996\u6B21\u89C2\u5BDF ${(get(e), untrack(() => get(e).first_observed_at || "\u2014")) ?? ""} \xB7 \u72B6\u6001 ${(get(e), untrack(() => get(e).state)) ?? ""}`);
                        set_text(text_72, (get(e), untrack(() => get(e).summary)));
                      });
                      event("click", button_46, () => openCanonical()(get(e).canonical_ref));
                      event("click", button_47, () => focusGraph("event:" + get(e).event_id));
                      append($$anchor7, div_50);
                    };
                    if_block(node_65, ($$render) => {
                      if (get(inspectorId), get(e), untrack(() => get(inspectorId) === get(e).event_id)) $$render(consequent_42);
                    });
                  }
                  reset(div_47);
                  template_effect(
                    ($0, $1, $2) => {
                      classes_7 = set_class(div_47, 1, "wh-timeline-row", null, classes_7, { compact: get(density) === "compact" });
                      classes_8 = set_class(span_17, 1, "wh-time-node", null, classes_8, {
                        approximate: get(e).time_precision !== "day",
                        corrected: get(e).has_corrected_claim,
                        contested: get(e).has_contested_claim
                      });
                      set_text(text_66, $0);
                      set_text(text_67, (get(e), untrack(() => get(e).title)));
                      set_text(text_68, $1);
                      set_text(text_70, `${$2 ?? ""} \xB7 ${(get(e), untrack(() => get(e).claim_count)) ?? ""} Claims \xB7 ${(get(e), untrack(() => get(e).source_count)) ?? ""} Sources`);
                    },
                    [
                      () => (get(e), untrack(() => dateLabel(get(e)))),
                      () => (get(e), untrack(() => get(e).thread_ids.map(threadName).join(" \xB7 "))),
                      () => (get(e), untrack(() => get(e).entity_ids.slice(0, 4).map(entityName).join(" \xB7 ")))
                    ]
                  );
                  event("click", button_41, stopPropagation(() => openEvent(get(e))));
                  event("keydown", div_47, (ev) => ev.key === "Enter" && !ev.target.closest(".wh-timeline-expanded") && inspectEvent(get(e).event_id));
                  event("click", div_47, (ev) => !ev.target.closest(".wh-timeline-expanded") && inspectEvent(get(e).event_id));
                  append($$anchor6, div_47);
                });
                append($$anchor5, fragment_10);
              };
              var d_8 = user_derived(() => (name(), untrack(() => !isMonthly() || periodOpen(name()))));
              if_block(node_60, ($$render) => {
                if (get(d_8)) $$render(consequent_43);
              });
            }
            template_effect(
              ($0) => {
                set_style(span_16, $0);
                set_attribute2(span_16, "title", (bucket(), untrack(() => `${bucket().count} Events \xB7 \u5F53\u524D\u8303\u56F4\u5185`)));
                set_text(text_65, `${(bucket(), untrack(() => bucket().count)) ?? ""} Events`);
              },
              [
                () => (bucket(), untrack(() => `width:${Math.min(100, Math.sqrt(bucket().count) * 12)}px`))
              ]
            );
            append($$anchor4, fragment_8);
          });
          var node_74 = sibling(node_58);
          {
            var consequent_44 = ($$anchor4) => {
              var div_57 = root_632();
              var button_49 = child(div_57);
              var span_20 = sibling(button_49);
              var text_80 = only_child(span_20);
              var button_50 = sibling(span_20);
              reset(div_57);
              template_effect(
                ($0) => {
                  button_49.disabled = get(timelineStart) === 0;
                  set_text(text_80, `\u663E\u793A ${get(timelineStart) + 1}\u2013${$0 ?? ""} / ${(get(visibleEvents), untrack(() => get(visibleEvents).length)) ?? ""}`);
                  button_50.disabled = (get(timelineStart), get(visibleEvents), untrack(() => get(timelineStart) + timelineWindow >= get(visibleEvents).length));
                },
                [
                  () => (get(timelineStart), get(visibleEvents), untrack(() => Math.min(get(timelineStart) + timelineWindow, get(visibleEvents).length)))
                ]
              );
              event("click", button_49, () => timelinePage(get(timelineStart) - timelineWindow));
              event("click", button_50, () => timelinePage(get(timelineStart) + timelineWindow));
              append($$anchor4, div_57);
            };
            if_block(node_74, ($$render) => {
              if (get(visibleEvents), untrack(() => get(visibleEvents).length > timelineWindow)) $$render(consequent_44);
            });
          }
          reset(section_9);
          template_effect(() => set_text(text_61, `${(get(visibleEvents), untrack(() => get(visibleEvents).length)) ?? ""} Events`));
          bind_select_value(select_7, () => get(group), ($$value) => set(group, $$value));
          bind_select_value(select_8, () => get(density), ($$value) => set(density, $$value));
          append($$anchor3, section_9);
        };
        var consequent_48 = ($$anchor3) => {
          var section_10 = root_68();
          var div_58 = child(section_10);
          var h2_3 = child(div_58);
          var small_17 = sibling(child(h2_3));
          var text_81 = only_child(small_17, true);
          reset(h2_3);
          var div_59 = sibling(h2_3);
          var label_11 = child(div_59);
          var select_9 = sibling(child(label_11));
          var option_22 = child(select_9);
          option_22.value = option_22.__value = "";
          var node_75 = sibling(option_22);
          each(
            node_75,
            1,
            () => (deep_read_state(repository()), untrack(() => [...new Set(repository().entities.map((e) => e.kind))].sort())),
            index,
            ($$anchor4, kind) => {
              var option_23 = root_43();
              var text_82 = only_child(option_23, true);
              var option_23_value = {};
              template_effect(() => {
                set_text(text_82, get(kind));
                if (option_23_value !== (option_23_value = get(kind))) {
                  option_23.value = (option_23.__value = option_23_value) ?? "";
                }
              });
              append($$anchor4, option_23);
            }
          );
          reset(select_9);
          init_select(select_9);
          reset(label_11);
          var label_12 = sibling(label_11);
          var input_3 = sibling(child(label_12));
          remove_input_defaults(input_3);
          reset(label_12);
          reset(div_59);
          reset(div_58);
          var node_76 = sibling(div_58);
          {
            var consequent_46 = ($$anchor4) => {
              var div_60 = root_65();
              var button_51 = sibling(child(div_60));
              reset(div_60);
              event("click", button_51, clearScope);
              append($$anchor4, div_60);
            };
            if_block(node_76, ($$render) => {
              if (get(visibleEntities), untrack(() => !get(visibleEntities).length)) $$render(consequent_46);
            });
          }
          var div_61 = sibling(node_76);
          each(
            div_61,
            5,
            () => (get(visibleEntities), untrack(() => get(visibleEntities).slice(0, 500))),
            index,
            ($$anchor4, entity) => {
              var button_52 = root_66();
              var strong_10 = child(button_52);
              var text_83 = only_child(strong_10, true);
              var span_21 = sibling(strong_10);
              var text_84 = only_child(span_21, true);
              var span_22 = sibling(span_21);
              var text_85 = only_child(span_22, true);
              var node_77 = sibling(span_22);
              ActivitySparkline(node_77, {
                get series() {
                  return get(entity), untrack(() => get(entity).activity_series);
                },
                width: 65,
                height: 18
              });
              var small_18 = sibling(node_77);
              var text_86 = only_child(small_18);
              reset(button_52);
              template_effect(
                ($0, $1) => {
                  set_text(text_83, (get(entity), untrack(() => get(entity).name)));
                  set_text(text_84, (get(entity), untrack(() => get(entity).kind)));
                  set_text(text_85, $0);
                  set_text(text_86, `${(get(entity), untrack(() => get(entity).thread_count)) ?? ""} Threads \xB7 ${(get(entity), untrack(() => get(entity).event_count)) ?? ""} Events \xB7 ${$1 ?? ""}`);
                },
                [
                  () => (get(entity), untrack(() => get(entity).thread_ids.slice(0, 2).map(threadName).join(" \xB7 "))),
                  () => (get(entity), untrack(() => formatDate(get(entity).last_seen_at)))
                ]
              );
              event("click", button_52, () => navigate("entity", get(entity).entity_id));
              append($$anchor4, button_52);
            }
          );
          reset(div_61);
          var node_78 = sibling(div_61);
          {
            var consequent_47 = ($$anchor4) => {
              var p_11 = root_67();
              append($$anchor4, p_11);
            };
            if_block(node_78, ($$render) => {
              if (get(visibleEntities), untrack(() => get(visibleEntities).length > 500)) $$render(consequent_47);
            });
          }
          reset(section_10);
          template_effect(() => set_text(text_81, (get(visibleEntities), untrack(() => get(visibleEntities).length))));
          bind_select_value(select_9, () => get(entityKind), ($$value) => set(entityKind, $$value));
          bind_value(input_3, () => get(minimumActivity), ($$value) => set(minimumActivity, $$value));
          append($$anchor3, section_10);
        };
        var consequent_51 = ($$anchor3) => {
          var section_11 = root_76();
          var div_62 = child(section_11);
          var div_63 = child(div_62);
          var button_53 = child(div_63);
          var h2_4 = sibling(button_53);
          var text_87 = only_child(h2_4, true);
          var span_23 = sibling(h2_4);
          var text_88 = only_child(span_23, true);
          reset(div_63);
          var button_54 = sibling(div_63);
          reset(div_62);
          var div_64 = sibling(div_62);
          var text_89 = only_child(div_64);
          var div_65 = sibling(div_64);
          each(div_65, 4, () => ["Overview", "Map", "Graph"], index, ($$anchor4, projection) => {
            var button_55 = root5();
            let classes_9;
            var text_90 = only_child(button_55, true);
            template_effect(() => {
              classes_9 = set_class(button_55, 1, "", null, classes_9, { active: get(entityProjection) === projection });
              set_text(text_90, projection);
            });
            event("click", button_55, () => set(entityProjection, projection));
            append($$anchor4, button_55);
          });
          reset(div_65);
          var node_79 = sibling(div_65);
          {
            var consequent_49 = ($$anchor4) => {
              var fragment_13 = root_732();
              var section_12 = first_child(fragment_13);
              var node_80 = sibling(child(section_12));
              each(
                node_80,
                1,
                () => (get(currentEntity), untrack(() => get(currentEntity).current_thread_ids || [])),
                index,
                ($$anchor5, id) => {
                  var button_56 = root_322();
                  var text_91 = only_child(button_56, true);
                  template_effect(($0) => set_text(text_91, $0), [() => (get(id), untrack(() => threadName(get(id))))]);
                  event("click", button_56, () => navigate("thread", get(id)));
                  append($$anchor5, button_56);
                },
                ($$anchor5) => {
                  var p_12 = root_69();
                  append($$anchor5, p_12);
                }
              );
              reset(section_12);
              var section_13 = sibling(section_12);
              var node_81 = sibling(child(section_13));
              each(
                node_81,
                1,
                () => (get(currentEntity), untrack(() => get(currentEntity).thread_ids)),
                index,
                ($$anchor5, id) => {
                  var button_57 = root_322();
                  var text_92 = only_child(button_57, true);
                  template_effect(($0) => set_text(text_92, $0), [() => (get(id), untrack(() => threadName(get(id))))]);
                  event("click", button_57, () => navigate("thread", get(id)));
                  append($$anchor5, button_57);
                },
                ($$anchor5) => {
                  var p_13 = root_70();
                  append($$anchor5, p_13);
                }
              );
              reset(section_13);
              var section_14 = sibling(section_13);
              var node_82 = sibling(child(section_14));
              ActivitySparkline(node_82, {
                get series() {
                  return get(currentEntity), untrack(() => get(currentEntity).activity_series);
                },
                width: 300,
                height: 64
              });
              var node_83 = sibling(node_82, 2);
              each(
                node_83,
                1,
                () => (get(currentEntity), deep_read_state(repository()), untrack(() => get(currentEntity).event_ids.map((id) => repository().eventById.get(id)).filter(Boolean).slice(-50).reverse())),
                index,
                ($$anchor5, e) => {
                  var button_58 = root_322();
                  var text_93 = only_child(button_58);
                  template_effect(($0) => set_text(text_93, `${$0 ?? ""} \xB7 ${(get(e), untrack(() => get(e).title)) ?? ""}`), [() => (get(e), untrack(() => dateLabel(get(e))))]);
                  event("click", button_58, () => openEvent(get(e)));
                  append($$anchor5, button_58);
                }
              );
              reset(section_14);
              var section_15 = sibling(section_14);
              var div_66 = sibling(child(section_15));
              each(
                div_66,
                5,
                () => (get(currentEntity), untrack(() => get(currentEntity).related_entity_ids || [])),
                index,
                ($$anchor5, id) => {
                  var button_59 = root5();
                  var text_94 = only_child(button_59, true);
                  template_effect(($0) => set_text(text_94, $0), [() => (get(id), untrack(() => entityName(get(id))))]);
                  event("click", button_59, () => navigate("entity", get(id)));
                  append($$anchor5, button_59);
                },
                ($$anchor5) => {
                  var p_14 = root_71();
                  append($$anchor5, p_14);
                }
              );
              reset(div_66);
              reset(section_15);
              var section_16 = sibling(section_15);
              var node_84 = sibling(child(section_16), 2);
              each(
                node_84,
                1,
                () => (get(currentEntity), untrack(() => get(currentEntity).contextual_questions?.filter((q) => q.state === "open") || [])),
                index,
                ($$anchor5, q) => {
                  var div_67 = root_722();
                  var strong_11 = child(div_67);
                  var text_95 = only_child(strong_11, true);
                  var button_60 = sibling(strong_11);
                  var text_96 = only_child(button_60, true);
                  reset(div_67);
                  template_effect(
                    ($0) => {
                      set_text(text_95, (get(q), untrack(() => get(q).question)));
                      set_text(text_96, $0);
                    },
                    [
                      () => (get(q), untrack(() => threadName(get(q).owner_thread_id)))
                    ]
                  );
                  event("click", button_60, () => navigate("thread", get(q).owner_thread_id));
                  append($$anchor5, div_67);
                },
                ($$anchor5) => {
                  var p_15 = root_27();
                  append($$anchor5, p_15);
                }
              );
              reset(section_16);
              append($$anchor4, fragment_13);
            };
            var consequent_50 = ($$anchor4) => {
              var section_17 = root_74();
              var node_85 = sibling(child(section_17));
              EntityProjection(node_85, {
                get entity() {
                  return get(currentEntity);
                },
                get repository() {
                  return repository();
                },
                get scope() {
                  return get(scope);
                },
                projection: "Map",
                openLocation: showLocation
              });
              reset(section_17);
              append($$anchor4, section_17);
            };
            var alternate_4 = ($$anchor4) => {
              var section_18 = root_75();
              var node_86 = sibling(child(section_18));
              EntityProjection(node_86, {
                get entity() {
                  return get(currentEntity);
                },
                get repository() {
                  return repository();
                },
                get scope() {
                  return get(scope);
                },
                projection: "Graph",
                openThread: (id) => navigate("thread", id),
                openEntity: (id) => navigate("entity", id)
              });
              var button_61 = sibling(node_86);
              reset(section_18);
              event("click", button_61, () => {
                navigate("graph", "", {
                  localContext: { type: "entity", id: get(currentEntity).entity_id }
                });
              });
              append($$anchor4, section_18);
            };
            if_block(node_79, ($$render) => {
              if (get(entityProjection) === "Overview") $$render(consequent_49);
              else if (get(entityProjection) === "Map") $$render(consequent_50, 1);
              else $$render(alternate_4, -1);
            });
          }
          reset(section_11);
          template_effect(
            ($0, $1) => {
              set_text(text_87, (get(currentEntity), untrack(() => get(currentEntity).name)));
              set_text(text_88, (get(currentEntity), untrack(() => get(currentEntity).kind)));
              set_text(text_89, `\u522B\u540D ${$0 ?? ""} \xB7 \u6700\u8FD1\u51FA\u73B0 ${$1 ?? ""} \xB7 Chronicle ID ${(get(currentEntity), untrack(() => get(currentEntity).entity_id)) ?? ""}`);
            },
            [
              () => (get(currentEntity), untrack(() => get(currentEntity).aliases.join("\u3001") || "\u2014")),
              () => (get(currentEntity), untrack(() => formatDate(get(currentEntity).last_seen_at)))
            ]
          );
          event("click", button_53, back);
          event("click", button_54, () => openCanonical()(get(currentEntity).canonical_ref));
          append($$anchor3, section_11);
        };
        var consequent_53 = ($$anchor3) => {
          var section_19 = root_822();
          var div_68 = child(section_19);
          var h2_5 = child(div_68);
          var small_19 = sibling(child(h2_5));
          var text_97 = only_child(small_19);
          reset(h2_5);
          var div_69 = sibling(h2_5);
          var label_13 = child(div_69);
          var select_10 = sibling(child(label_13));
          var option_24 = child(select_10);
          option_24.value = option_24.__value = "events";
          var option_25 = sibling(option_24);
          option_25.value = option_25.__value = "threads";
          var option_26 = sibling(option_25);
          option_26.value = option_26.__value = "entities";
          reset(select_10);
          init_select(select_10);
          reset(label_13);
          var button_62 = sibling(label_13);
          var button_63 = sibling(button_62);
          var button_64 = sibling(button_63);
          reset(div_69);
          reset(div_68);
          var node_87 = sibling(div_68);
          {
            var consequent_52 = ($$anchor4) => {
              var div_70 = root_77();
              var button_65 = sibling(child(div_70));
              reset(div_70);
              event("click", button_65, clearScope);
              append($$anchor4, div_70);
            };
            var alternate_5 = ($$anchor4) => {
              var div_71 = root_81();
              var svg = child(div_71);
              var g = sibling(child(svg));
              var path = child(g);
              var node_88 = sibling(path);
              each(node_88, 0, () => [-180, -120, -60, 0, 60, 120, 180], index, ($$anchor5, lon) => {
                var line = root_78();
                template_effect(() => {
                  set_attribute2(line, "x1", (lon + 180) * 2.5);
                  set_attribute2(line, "x2", (lon + 180) * 2.5);
                });
                append($$anchor5, line);
              });
              var node_89 = sibling(node_88);
              each(node_89, 0, () => [-60, -30, 0, 30, 60], index, ($$anchor5, lat) => {
                var line_1 = root_79();
                template_effect(() => {
                  set_attribute2(line_1, "y1", (90 - lat) * 2.5);
                  set_attribute2(line_1, "y2", (90 - lat) * 2.5);
                });
                append($$anchor5, line_1);
              });
              var node_90 = sibling(node_89);
              each(node_90, 1, () => get(markerClusters), index, ($$anchor5, marker) => {
                var g_1 = root_80();
                let classes_10;
                var title = child(g_1);
                var text_98 = only_child(title, true);
                var circle = sibling(title);
                var text_99 = sibling(circle);
                var text_100 = only_child(text_99, true);
                reset(g_1);
                template_effect(
                  ($0, $1, $2) => {
                    classes_10 = set_class(g_1, 0, "wh-map-marker", null, classes_10, { focused: $0, approximate: $1 });
                    set_attribute2(g_1, "transform", (get(marker), get(zoom), untrack(() => `translate(${(get(marker).lon + 180) * 2.5},${(90 - get(marker).lat) * 2.5}) scale(${1 / get(zoom)})`)));
                    set_text(text_98, (get(marker), get(mapMode), untrack(() => get(marker).locations.length > 1 ? `${get(marker).locations.length} \u4E2A\u5730\u70B9 \xB7 ${get(marker).count} ${get(mapMode)}` : `${get(marker).locations[0].name} \xB7 ${get(marker).count} ${get(mapMode)} \xB7 ${get(marker).locations[0].geo_precision}`)));
                    set_attribute2(circle, "r", $2);
                    set_text(text_100, (get(marker), untrack(() => get(marker).count)));
                  },
                  [
                    () => get(marker).locations.some((l) => l.location_id === get(selectedLocation)),
                    () => get(marker).locations.some((l) => !["exact", "city"].includes(l.geo_precision)),
                    () => (get(marker), untrack(() => Math.min(26, 9 + Math.sqrt(get(marker).count) * 3)))
                  ]
                );
                event("click", g_1, () => mapPick(get(marker)));
                event("keydown", g_1, (e) => e.key === "Enter" && mapPick(get(marker)));
                append($$anchor5, g_1);
              });
              reset(g);
              reset(svg);
              next();
              reset(div_71);
              template_effect(() => {
                set_attribute2(g, "transform", (get(zoom), get(mapCenter), untrack(() => `translate(450,225) scale(${get(zoom)}) translate(${get(zoom) === 1 ? -450 : -(get(mapCenter).lon + 180) * 2.5},${get(zoom) === 1 ? -225 : -(90 - get(mapCenter).lat) * 2.5})`)));
                set_attribute2(path, "d", world_path_default);
              });
              append($$anchor4, div_71);
            };
            if_block(node_87, ($$render) => {
              if (get(locationPoints), untrack(() => !get(locationPoints).length)) $$render(consequent_52);
              else $$render(alternate_5, -1);
            });
          }
          reset(section_19);
          template_effect(() => set_text(text_97, `${(get(locationPoints), untrack(() => get(locationPoints).length)) ?? ""} Locations`));
          bind_select_value(select_10, () => get(mapMode), ($$value) => set(mapMode, $$value));
          event("click", button_62, () => set(zoom, Math.min(8, get(zoom) * 2)));
          event("click", button_63, () => set(zoom, Math.max(1, get(zoom) / 2)));
          event("click", button_64, () => {
            set(zoom, 1);
            set(mapCenter, { lat: 0, lon: 0 });
          });
          append($$anchor3, section_19);
        };
        var consequent_62 = ($$anchor3) => {
          var section_20 = root_97();
          var div_72 = child(section_20);
          var h2_6 = child(div_72);
          var small_20 = sibling(child(h2_6));
          var text_101 = only_child(small_20);
          reset(h2_6);
          var div_73 = sibling(h2_6);
          var label_14 = child(div_73);
          var select_11 = sibling(child(label_14));
          var select_11_value;
          init_select(select_11);
          reset(label_14);
          var label_15 = sibling(label_14);
          var select_12 = sibling(child(label_15));
          var option_27 = child(select_12);
          option_27.value = option_27.__value = "radial";
          var option_28 = sibling(option_27);
          option_28.value = option_28.__value = "force";
          var option_29 = sibling(option_28);
          option_29.value = option_29.__value = "hierarchical";
          reset(select_12);
          init_select(select_12);
          reset(label_15);
          var label_16 = sibling(label_15);
          var select_13 = sibling(child(label_16));
          var option_30 = child(select_13);
          option_30.value = option_30.__value = 1;
          var option_31 = sibling(option_30);
          option_31.value = option_31.__value = 2;
          var option_32 = sibling(option_31);
          option_32.value = option_32.__value = 3;
          reset(select_13);
          init_select(select_13);
          reset(label_16);
          var label_17 = sibling(label_16);
          var input_4 = sibling(child(label_17));
          remove_input_defaults(input_4);
          reset(label_17);
          var button_66 = sibling(label_17);
          reset(div_73);
          reset(div_72);
          var div_74 = sibling(div_72);
          var node_91 = sibling(child(div_74));
          each(
            node_91,
            0,
            () => [
              "thread",
              "event",
              "entity",
              "location",
              "claim",
              "source",
              "question"
            ],
            index,
            ($$anchor4, type) => {
              var label_18 = root_832();
              var input_5 = child(label_18);
              remove_input_defaults(input_5);
              var text_102 = sibling(input_5, 1, true);
              reset(label_18);
              template_effect(
                ($0) => {
                  set_checked(input_5, $0);
                  set_text(text_102, type);
                },
                [
                  () => (get(graphNodeTypes), type, untrack(() => get(graphNodeTypes).has(type)))
                ]
              );
              event("change", input_5, () => toggleType(type));
              append($$anchor4, label_18);
            }
          );
          var select_14 = sibling(node_91, 2);
          var option_33 = child(select_14);
          option_33.value = option_33.__value = "";
          var node_92 = sibling(option_33);
          each(
            node_92,
            1,
            () => (deep_read_state(repository()), untrack(() => repository().graphEdgeTypes())),
            index,
            ($$anchor4, type) => {
              var option_34 = root_43();
              var text_103 = only_child(option_34);
              var option_34_value = {};
              template_effect(
                ($0) => {
                  set_text(text_103, `${$0 ?? ""}${get(type) ?? ""}`);
                  if (option_34_value !== (option_34_value = get(type))) {
                    option_34.value = (option_34.__value = option_34_value) ?? "";
                  }
                },
                [
                  () => (get(graphEdgeTypes), get(type), untrack(() => get(graphEdgeTypes).has(get(type)) ? "\u2713 " : ""))
                ]
              );
              append($$anchor4, option_34);
            }
          );
          reset(select_14);
          var node_93 = sibling(select_14);
          {
            var consequent_54 = ($$anchor4) => {
              var button_67 = root_84();
              event("click", button_67, () => set(graphEdgeTypes, /* @__PURE__ */ new Set()));
              append($$anchor4, button_67);
            };
            if_block(node_93, ($$render) => {
              if (get(graphEdgeTypes), untrack(() => get(graphEdgeTypes).size)) $$render(consequent_54);
            });
          }
          var input_6 = sibling(node_93);
          reset(div_74);
          var node_94 = sibling(div_74, 2);
          {
            var consequent_56 = ($$anchor4) => {
              var div_75 = root_87();
              var node_95 = child(div_75);
              {
                var consequent_55 = ($$anchor5) => {
                  var fragment_14 = root_85();
                  var text_104 = first_child(fragment_14);
                  var button_68 = sibling(text_104);
                  template_effect(() => set_text(text_104, `\u56FE\u7D22\u5F15\u65E0\u6548\uFF1A${(deep_read_state(repository()), untrack(() => repository().graphFault)) ?? ""} `));
                  event("click", button_68, function(...$$args) {
                    refresh()?.apply(this, $$args);
                  });
                  append($$anchor5, fragment_14);
                };
                var alternate_6 = ($$anchor5) => {
                  var fragment_15 = root_86();
                  var button_69 = sibling(first_child(fragment_15));
                  event("click", button_69, clearScope);
                  append($$anchor5, fragment_15);
                };
                if_block(node_95, ($$render) => {
                  if (deep_read_state(repository()), untrack(() => repository().graphFault)) $$render(consequent_55);
                  else $$render(alternate_6, -1);
                });
              }
              reset(div_75);
              append($$anchor4, div_75);
            };
            var alternate_8 = ($$anchor4) => {
              var div_76 = root_96();
              var svg_1 = child(div_76);
              var node_96 = child(svg_1);
              each(node_96, 1, () => (get(graphSlice), untrack(() => get(graphSlice).edges)), index, ($$anchor5, edge) => {
                const a = derived_safe_equal(() => (get(graphSlice), get(edge), untrack(() => get(graphSlice).nodes.findIndex((n) => n.id === get(edge).source))));
                const b = derived_safe_equal(() => (get(graphSlice), get(edge), untrack(() => get(graphSlice).nodes.findIndex((n) => n.id === get(edge).target))));
                var line_2 = root_88();
                let classes_11;
                var title_1 = child(line_2);
                var text_105 = only_child(title_1, true);
                reset(line_2);
                template_effect(
                  ($0, $1, $2, $3) => {
                    set_attribute2(line_2, "x1", $0);
                    set_attribute2(line_2, "y1", $1);
                    set_attribute2(line_2, "x2", $2);
                    set_attribute2(line_2, "y2", $3);
                    classes_11 = set_class(line_2, 0, "wh-graph-edge", null, classes_11, { explicit: !!get(edge).canonical_ref });
                    set_text(text_105, (get(edge), untrack(() => get(edge).type)));
                  },
                  [
                    () => (deep_read_state(get(a)), get(graphSlice), get(edge), untrack(() => graphPosition(get(a), get(graphSlice).nodes.length, get(edge).source).x)),
                    () => (deep_read_state(get(a)), get(graphSlice), get(edge), untrack(() => graphPosition(get(a), get(graphSlice).nodes.length, get(edge).source).y)),
                    () => (deep_read_state(get(b)), get(graphSlice), get(edge), untrack(() => graphPosition(get(b), get(graphSlice).nodes.length, get(edge).target).x)),
                    () => (deep_read_state(get(b)), get(graphSlice), get(edge), untrack(() => graphPosition(get(b), get(graphSlice).nodes.length, get(edge).target).y))
                  ]
                );
                event("keydown", line_2, (ev) => ev.key === "Enter" && graphChooseEdge(get(edge)));
                event("click", line_2, () => graphChooseEdge(get(edge)));
                append($$anchor5, line_2);
              });
              var node_97 = sibling(node_96);
              each(node_97, 1, () => (get(graphSlice), untrack(() => get(graphSlice).nodes)), index, ($$anchor5, node, i) => {
                var g_2 = root_95();
                let classes_12;
                var node_98 = child(g_2);
                {
                  var consequent_57 = ($$anchor6) => {
                    var rect = root_89();
                    append($$anchor6, rect);
                  };
                  var consequent_58 = ($$anchor6) => {
                    var polygon = root_90();
                    let classes_13;
                    template_effect(() => {
                      set_attribute2(polygon, "points", (get(node), untrack(() => get(node).type === "claim" ? "0,-11 11,0 0,11 -11,0" : "0,-12 10,0 0,12 -10,0")));
                      classes_13 = set_class(polygon, 0, "", null, classes_13, {
                        "wh-node-claim": get(node).type === "claim",
                        "wh-node-location": get(node).type === "location"
                      });
                    });
                    append($$anchor6, polygon);
                  };
                  var consequent_59 = ($$anchor6) => {
                    var rect_1 = root_91();
                    append($$anchor6, rect_1);
                  };
                  var consequent_60 = ($$anchor6) => {
                    var circle_1 = root_922();
                    append($$anchor6, circle_1);
                  };
                  var alternate_7 = ($$anchor6) => {
                    var circle_2 = root_93();
                    let classes_14;
                    template_effect(() => {
                      set_attribute2(circle_2, "r", (get(node), untrack(() => get(node).type === "entity" ? 10 : 7)));
                      classes_14 = set_class(circle_2, 0, "", null, classes_14, {
                        entity: get(node).type === "entity",
                        event: get(node).type === "event"
                      });
                    });
                    append($$anchor6, circle_2);
                  };
                  if_block(node_98, ($$render) => {
                    if (get(node), untrack(() => get(node).type === "thread")) $$render(consequent_57);
                    else if (get(node), untrack(() => get(node).type === "claim" || get(node).type === "location")) $$render(consequent_58, 1);
                    else if (get(node), untrack(() => get(node).type === "source")) $$render(consequent_59, 2);
                    else if (get(node), untrack(() => get(node).type === "question")) $$render(consequent_60, 3);
                    else $$render(alternate_7, -1);
                  });
                }
                var node_99 = sibling(node_98);
                {
                  var consequent_61 = ($$anchor6) => {
                    var text_106 = root_94();
                    var text_107 = only_child(text_106, true);
                    template_effect(($0) => set_text(text_107, $0), [
                      () => (get(node), untrack(() => get(node).label.slice(0, 18)))
                    ]);
                    append($$anchor6, text_106);
                  };
                  if_block(node_99, ($$render) => {
                    if (get(graphSlice), get(node), get(selectedNode), untrack(() => get(graphSlice).nodes.length <= 25 || get(node).type === "thread" || get(node).id === get(selectedNode))) $$render(consequent_61);
                  });
                }
                var title_2 = sibling(node_99);
                var text_108 = only_child(title_2);
                reset(g_2);
                template_effect(
                  ($0) => {
                    set_attribute2(g_2, "transform", $0);
                    classes_12 = set_class(g_2, 0, "wh-graph-node", null, classes_12, { focused: get(selectedNode) === get(node).id });
                    set_text(text_108, `${(get(node), untrack(() => get(node).type)) ?? ""}: ${(get(node), untrack(() => get(node).label)) ?? ""}`);
                  },
                  [
                    () => (i, get(graphSlice), get(node), untrack(() => `translate(${graphPosition(i, get(graphSlice).nodes.length, get(node).id).x},${graphPosition(i, get(graphSlice).nodes.length, get(node).id).y})`))
                  ]
                );
                event("click", g_2, () => graphChooseNode(get(node).id));
                event("keydown", g_2, (e) => e.key === "Enter" && graphChooseNode(get(node).id));
                append($$anchor5, g_2);
              });
              reset(svg_1);
              reset(div_76);
              append($$anchor4, div_76);
            };
            if_block(node_94, ($$render) => {
              if (get(graphSlice), untrack(() => !get(graphSlice).nodes.length)) $$render(consequent_56);
              else $$render(alternate_8, -1);
            });
          }
          reset(section_20);
          template_effect(() => {
            set_text(text_101, `${(get(graphSlice), untrack(() => get(graphSlice).nodes.length)) ?? ""} Nodes \xB7 ${(get(graphSlice), untrack(() => get(graphSlice).edges.length)) ?? ""} Edges`);
            if (select_11_value !== (select_11_value = get(graphPreset))) {
              select_11.value = (select_11.__value = select_11_value) ?? "", select_option(select_11, select_11_value);
            }
          });
          event("change", select_11, (e) => choosePreset(e.currentTarget.value));
          bind_select_value(select_12, () => get(graphLayout), ($$value) => set(graphLayout, $$value));
          bind_select_value(select_13, () => get(depth), ($$value) => set(depth, $$value));
          bind_value(input_4, () => get(maxNodes), ($$value) => set(maxNodes, $$value));
          event("click", button_66, () => {
            set(selectedNode, "");
            set(hidden, /* @__PURE__ */ new Set());
            set(expanded, /* @__PURE__ */ new Set());
            set(pinned, /* @__PURE__ */ new Set());
            set(pinnedPositions, /* @__PURE__ */ new Map());
            update(graphRefresh);
          });
          event("change", select_14, (e) => e.currentTarget.value && toggleEdge(e.currentTarget.value));
          event("change", input_6, (e) => {
            const term = e.currentTarget.value.toLocaleLowerCase();
            const match = get(graphSlice).nodes.find((n) => n.label.toLocaleLowerCase().includes(term));
            if (match) graphChooseNode(match.id);
          });
          append($$anchor3, section_20);
        };
        if_block(node_14, ($$render) => {
          if (get(page) === "threads") $$render(consequent_13);
          else if (get(page) === "thread" && get(currentThread)) $$render(consequent_33, 1);
          else if (get(page) === "timeline") $$render(consequent_45, 2);
          else if (get(page) === "entities") $$render(consequent_48, 3);
          else if (get(page) === "entity" && get(currentEntity)) $$render(consequent_51, 4);
          else if (get(page) === "map") $$render(consequent_53, 5);
          else if (get(page) === "graph") $$render(consequent_62, 6);
        });
      }
      var node_100 = sibling(node_14, 2);
      {
        var consequent_79 = ($$anchor3) => {
          var aside_1 = root_1122();
          let classes_15;
          var button_70 = child(aside_1);
          var node_101 = sibling(button_70);
          {
            var consequent_64 = ($$anchor4) => {
              var fragment_16 = root_99();
              var h3_2 = first_child(fragment_16);
              var text_109 = only_child(h3_2, true);
              var p_16 = sibling(h3_2);
              var text_110 = only_child(p_16);
              var p_17 = sibling(p_16);
              var text_111 = only_child(p_17);
              var p_18 = sibling(p_17);
              var text_112 = only_child(p_18);
              var p_19 = sibling(p_18);
              var text_113 = only_child(p_19);
              var node_102 = sibling(p_19, 2);
              {
                var consequent_63 = ($$anchor5) => {
                  var button_71 = root_98();
                  event("click", button_71, () => openCanonical()(get(selectedEdge).canonical_ref));
                  append($$anchor5, button_71);
                };
                if_block(node_102, ($$render) => {
                  if (get(selectedEdge), untrack(() => get(selectedEdge).canonical_ref?.kind === "chronicle")) $$render(consequent_63);
                });
              }
              template_effect(
                ($0) => {
                  set_text(text_109, (get(selectedEdge), untrack(() => get(selectedEdge).type)));
                  set_text(text_110, `\u65B9\u5411\uFF1A${(get(selectedEdge), untrack(() => get(selectedEdge).source)) ?? ""} \u2192 ${(get(selectedEdge), untrack(() => get(selectedEdge).target)) ?? ""}`);
                  set_text(text_111, `\u7F6E\u4FE1\u5EA6\uFF1A${(get(selectedEdge), untrack(() => get(selectedEdge).confidence ?? "\u672A\u63D0\u4F9B")) ?? ""}`);
                  set_text(text_112, `\u8BC1\u636E\u5F15\u7528\uFF1A${$0 ?? ""}`);
                  set_text(text_113, `\u6765\u6E90\uFF1A${(get(selectedEdge), untrack(() => get(selectedEdge).canonical_ref ? "Chronicle Relation" : "\u6295\u5F71\u7ED3\u6784\u5173\u7CFB")) ?? ""}`);
                },
                [
                  () => (get(selectedEdge), untrack(() => JSON.stringify(get(selectedEdge).evidence_refs || []).slice(0, 300)))
                ]
              );
              append($$anchor4, fragment_16);
            };
            var consequent_71 = ($$anchor4) => {
              const node = derived_safe_equal(() => (deep_read_state(repository()), get(selectedNode), untrack(() => repository().graphNode(get(selectedNode)))));
              var fragment_17 = root_103();
              var h3_3 = first_child(fragment_17);
              var text_114 = only_child(h3_3, true);
              var p_20 = sibling(h3_3);
              var text_115 = only_child(p_20);
              var node_103 = sibling(p_20);
              {
                var consequent_65 = ($$anchor5) => {
                  var p_21 = root_55();
                  var text_116 = only_child(p_21);
                  template_effect(() => set_text(text_116, `\u7F6E\u4FE1\u5EA6\uFF1A${(deep_read_state(get(node)), untrack(() => get(node).confidence)) ?? ""}`));
                  append($$anchor5, p_21);
                };
                if_block(node_103, ($$render) => {
                  if (deep_read_state(get(node)), untrack(() => get(node)?.confidence != null)) $$render(consequent_65);
                });
              }
              var node_104 = sibling(node_103);
              {
                var consequent_66 = ($$anchor5) => {
                  var p_22 = root_100();
                  var text_117 = only_child(p_22, true);
                  template_effect(() => set_text(text_117, (deep_read_state(get(node)), untrack(() => get(node).summary))));
                  append($$anchor5, p_22);
                };
                if_block(node_104, ($$render) => {
                  if (deep_read_state(get(node)), untrack(() => get(node)?.summary)) $$render(consequent_66);
                });
              }
              var node_105 = sibling(node_104);
              {
                var consequent_67 = ($$anchor5) => {
                  var p_23 = root_55();
                  var text_118 = only_child(p_23);
                  template_effect(() => set_text(text_118, `\u6D3B\u52A8\uFF1A${(deep_read_state(get(node)), untrack(() => get(node).activity_events_12w)) ?? ""} Events / \u622A\u81F3\u6700\u65B0 Event \u7684 12 \u5468`));
                  append($$anchor5, p_23);
                };
                if_block(node_105, ($$render) => {
                  if (deep_read_state(get(node)), untrack(() => get(node)?.activity_events_12w != null)) $$render(consequent_67);
                });
              }
              var node_106 = sibling(node_105);
              {
                var consequent_68 = ($$anchor5) => {
                  var p_24 = root_55();
                  var text_119 = only_child(p_24);
                  template_effect(() => set_text(text_119, `\u5730\u70B9\u7CBE\u5EA6\uFF1A${(deep_read_state(get(node)), untrack(() => get(node).geo_precision)) ?? ""}`));
                  append($$anchor5, p_24);
                };
                if_block(node_106, ($$render) => {
                  if (deep_read_state(get(node)), untrack(() => get(node)?.geo_precision)) $$render(consequent_68);
                });
              }
              var p_25 = sibling(node_106);
              var text_120 = only_child(p_25);
              var node_107 = sibling(p_25, 2);
              each(
                node_107,
                1,
                () => (get(graphSlice), get(selectedNode), untrack(() => get(graphSlice).edges.filter((e) => e.source === get(selectedNode) || e.target === get(selectedNode)).slice(0, 8))),
                index,
                ($$anchor5, relation) => {
                  var button_72 = root_322();
                  var text_121 = only_child(button_72);
                  template_effect(($0) => set_text(text_121, `${(get(relation), untrack(() => get(relation).type)) ?? ""} \u2192 ${$0 ?? ""}`), [
                    () => (deep_read_state(repository()), get(relation), get(selectedNode), untrack(() => repository().graphNode(get(relation).source === get(selectedNode) ? get(relation).target : get(relation).source)?.label || "\u672A\u77E5\u5BF9\u8C61"))
                  ]);
                  event("click", button_72, () => graphChooseEdge(get(relation)));
                  append($$anchor5, button_72);
                }
              );
              var button_73 = sibling(node_107);
              var text_122 = only_child(button_73, true);
              var button_74 = sibling(button_73);
              var button_75 = sibling(button_74);
              var text_123 = only_child(button_75, true);
              var button_76 = sibling(button_75);
              var node_108 = sibling(button_76);
              {
                var consequent_69 = ($$anchor5) => {
                  var fragment_18 = root_101();
                  var button_77 = first_child(fragment_18);
                  var button_78 = sibling(button_77);
                  event("click", button_77, () => {
                    setScope("entityId", get(selectedNode).slice(7));
                    navigate("timeline");
                  });
                  event("click", button_78, () => {
                    setScope("entityId", get(selectedNode).slice(7));
                    navigate("threads");
                  });
                  append($$anchor5, fragment_18);
                };
                if_block(node_108, ($$render) => {
                  if (deep_read_state(get(node)), untrack(() => get(node)?.type === "entity")) $$render(consequent_69);
                });
              }
              var node_109 = sibling(node_108);
              {
                var consequent_70 = ($$anchor5) => {
                  var button_79 = root_1022();
                  event("click", button_79, () => openCanonical()(get(node).canonical_ref));
                  append($$anchor5, button_79);
                };
                if_block(node_109, ($$render) => {
                  if (deep_read_state(get(node)), untrack(() => get(node)?.canonical_ref?.kind === "chronicle")) $$render(consequent_70);
                });
              }
              template_effect(
                ($0, $1, $2) => {
                  set_text(text_114, (deep_read_state(get(node)), get(selectedNode), untrack(() => get(node)?.label || get(selectedNode))));
                  set_text(text_115, `${(deep_read_state(get(node)), untrack(() => get(node)?.type)) ?? ""}${(deep_read_state(get(node)), untrack(() => get(node)?.state ? ` \xB7 ${get(node).state}` : "")) ?? ""}${(deep_read_state(get(node)), untrack(() => get(node)?.publisher ? ` \xB7 ${get(node).publisher}` : "")) ?? ""}`);
                  set_text(text_120, `\u5173\u7CFB\uFF1A\u5168\u5C40 ${(deep_read_state(get(node)), untrack(() => get(node)?.relation_count ?? "\u2014")) ?? ""} \xB7 \u5F53\u524D\u56FE ${$0 ?? ""}`);
                  set_text(text_122, $1);
                  set_text(text_123, $2);
                },
                [
                  () => (get(graphSlice), get(selectedNode), untrack(() => get(graphSlice).edges.filter((e) => e.source === get(selectedNode) || e.target === get(selectedNode)).length)),
                  () => (get(expanded), get(selectedNode), untrack(() => get(expanded).has(get(selectedNode)) ? "\u6536\u8D77\u90BB\u5C45" : "\u5C55\u5F00\u90BB\u5C45")),
                  () => (get(pinned), get(selectedNode), untrack(() => get(pinned).has(get(selectedNode)) ? "\u53D6\u6D88\u56FA\u5B9A" : "\u56FA\u5B9A"))
                ]
              );
              event("click", button_73, () => toggleSet((v) => set(expanded, v), get(selectedNode), get(expanded)));
              event("click", button_74, () => hideNode(get(selectedNode)));
              event("click", button_75, () => togglePin(get(selectedNode)));
              event("click", button_76, () => openGraphNode(get(selectedNode)));
              append($$anchor4, fragment_17);
            };
            var consequent_74 = ($$anchor4) => {
              const l = derived_safe_equal(() => (deep_read_state(repository()), get(selectedLocation), untrack(() => repository().locationById.get(get(selectedLocation)))));
              var fragment_19 = root_106();
              var h3_4 = first_child(fragment_19);
              var text_124 = only_child(h3_4, true);
              var node_110 = sibling(h3_4);
              {
                var consequent_72 = ($$anchor5) => {
                  var div_77 = root_47();
                  each(div_77, 5, () => get(selectedCluster), index, ($$anchor6, id) => {
                    var button_80 = root5();
                    var text_125 = only_child(button_80, true);
                    template_effect(($0) => set_text(text_125, $0), [
                      () => (deep_read_state(repository()), get(id), untrack(() => repository().locationById.get(get(id))?.name || get(id)))
                    ]);
                    event("click", button_80, () => {
                      set(selectedLocation, get(id));
                      set(selectedCluster, [get(id)]);
                    });
                    append($$anchor6, button_80);
                  });
                  reset(div_77);
                  append($$anchor5, div_77);
                };
                if_block(node_110, ($$render) => {
                  if (get(selectedCluster), untrack(() => get(selectedCluster).length > 1)) $$render(consequent_72);
                });
              }
              var p_26 = sibling(node_110);
              var text_126 = only_child(p_26);
              var p_27 = sibling(p_26);
              var text_127 = only_child(p_27);
              var p_28 = sibling(p_27);
              var text_128 = only_child(p_28);
              var p_29 = sibling(p_28);
              var text_129 = only_child(p_29);
              var div_78 = sibling(p_29, 2);
              each(
                div_78,
                5,
                () => (get(selectedLocation), untrack(() => [
                  ...new Set(locationEvents(get(selectedLocation)).flatMap((e) => e.entity_ids))
                ].slice(0, 6))),
                index,
                ($$anchor5, id) => {
                  var button_81 = root5();
                  var text_130 = only_child(button_81, true);
                  template_effect(($0) => set_text(text_130, $0), [() => (get(id), untrack(() => entityName(get(id))))]);
                  event("click", button_81, () => navigate("entity", get(id)));
                  append($$anchor5, button_81);
                },
                ($$anchor5) => {
                  var span_24 = root_104();
                  append($$anchor5, span_24);
                }
              );
              reset(div_78);
              var node_111 = sibling(div_78);
              {
                var consequent_73 = ($$anchor5) => {
                  var button_82 = root_105();
                  event("click", button_82, () => openCanonical()(get(l).canonical_source_ref));
                  append($$anchor5, button_82);
                };
                if_block(node_111, ($$render) => {
                  if (deep_read_state(get(l)), untrack(() => get(l)?.canonical_source_ref?.kind === "chronicle")) $$render(consequent_73);
                });
              }
              var node_112 = sibling(node_111, 2);
              each(
                node_112,
                1,
                () => (get(selectedLocation), untrack(() => locationEvents(get(selectedLocation)).slice(0, 5))),
                index,
                ($$anchor5, e) => {
                  var button_83 = root_322();
                  var text_131 = only_child(button_83);
                  template_effect(($0) => set_text(text_131, `${$0 ?? ""} \xB7 ${(get(e), untrack(() => get(e).title)) ?? ""}`), [() => (get(e), untrack(() => dateLabel(get(e))))]);
                  event("click", button_83, () => openEvent(get(e)));
                  append($$anchor5, button_83);
                }
              );
              var button_84 = sibling(node_112);
              var button_85 = sibling(button_84);
              var button_86 = sibling(button_85);
              var node_113 = sibling(button_86);
              each(
                node_113,
                1,
                () => (deep_read_state(get(l)), untrack(() => get(l)?.thread_ids || [])),
                index,
                ($$anchor5, id) => {
                  var button_87 = root_322();
                  var text_132 = only_child(button_87, true);
                  template_effect(($0) => set_text(text_132, $0), [() => (get(id), untrack(() => threadName(get(id))))]);
                  event("click", button_87, () => navigate("thread", get(id)));
                  append($$anchor5, button_87);
                }
              );
              template_effect(
                ($0, $1) => {
                  set_text(text_124, (get(selectedCluster), deep_read_state(get(l)), get(selectedLocation), untrack(() => get(selectedCluster).length > 1 ? `${get(selectedCluster).length} \u4E2A\u5730\u70B9` : get(l)?.name || get(selectedLocation))));
                  set_text(text_126, `\u7CBE\u5EA6\uFF1A${(deep_read_state(get(l)), untrack(() => get(l)?.geo_precision)) ?? ""} \xB7 \u5750\u6807\uFF1A${(deep_read_state(get(l)), untrack(() => get(l)?.lat)) ?? ""}, ${(deep_read_state(get(l)), untrack(() => get(l)?.lon)) ?? ""}`);
                  set_text(text_127, `\u5730\u7406\u6765\u6E90\uFF1A${(deep_read_state(get(l)), untrack(() => get(l)?.canonical_source_ref?.kind || "\u672A\u77E5")) ?? ""}${(deep_read_state(get(l)), untrack(() => get(l)?.canonical_source_ref?.id ? ` \xB7 ${get(l).canonical_source_ref.id}` : "")) ?? ""}`);
                  set_text(text_128, `${$0 ?? ""} Events \xB7 ${(deep_read_state(get(l)), untrack(() => get(l)?.thread_ids.length)) ?? ""} Threads`);
                  set_text(text_129, `\u65E5\u671F\uFF1A${$1 ?? ""}`);
                },
                [
                  () => (get(selectedLocation), untrack(() => locationEvents(get(selectedLocation)).length)),
                  () => (get(selectedLocation), untrack(() => locationEvents(get(selectedLocation)).length ? `${dateOf(locationEvents(get(selectedLocation)).at(-1))} \u2192 ${dateOf(locationEvents(get(selectedLocation))[0])}` : "\u2014"))
                ]
              );
              event("click", button_84, () => filterLocation(get(selectedLocation)));
              event("click", button_85, () => {
                setScope("locationId", get(selectedLocation));
                navigate("threads");
              });
              event("click", button_86, () => {
                setScope("locationId", get(selectedLocation));
                set(selectedNode, "location:" + get(selectedLocation));
                update(graphRefresh);
                navigate("graph");
                set(showInspector, true);
              });
              append($$anchor4, fragment_19);
            };
            var consequent_75 = ($$anchor4) => {
              var div_79 = root_108();
              var h3_5 = sibling(child(div_79));
              var text_133 = only_child(h3_5, true);
              var p_30 = sibling(h3_5);
              var text_134 = only_child(p_30, true);
              var div_80 = sibling(p_30);
              each(div_80, 4, () => ["Time", "Graph", "Map"], index, ($$anchor5, projection) => {
                var button_88 = root5();
                let classes_16;
                var text_135 = only_child(button_88, true);
                template_effect(() => {
                  classes_16 = set_class(button_88, 1, "", null, classes_16, { active: get(inspectorProjection) === projection });
                  set_text(text_135, projection);
                });
                event("click", button_88, () => set(inspectorProjection, projection));
                append($$anchor5, button_88);
              });
              reset(div_80);
              var node_114 = sibling(div_80);
              ThreadProjection(node_114, {
                get thread() {
                  return get(homeThread);
                },
                get repository() {
                  return repository();
                },
                get scope() {
                  return get(scope);
                },
                get projection() {
                  return get(inspectorProjection);
                },
                openEvent: (e) => {
                  navigate("thread", get(homeThread).thread_id, { eventId: e.event_id });
                  set(threadProjection, "Timeline");
                },
                openEntity: (id) => navigate("entity", id),
                openLocation: showLocation
              });
              var h4 = sibling(node_114);
              var text_136 = only_child(h4);
              var node_115 = sibling(h4);
              each(
                node_115,
                1,
                () => (get(homeThread), untrack(() => get(homeThread).open_questions?.filter((q) => q.state === "open").slice(0, 3) || [])),
                index,
                ($$anchor5, question) => {
                  var button_89 = root_107();
                  var text_137 = only_child(button_89);
                  template_effect(() => {
                    set_attribute2(button_89, "title", (get(question), untrack(() => get(question).question)));
                    set_text(text_137, `\u25CB ${(get(question), untrack(() => get(question).question)) ?? ""}`);
                  });
                  event("click", button_89, () => openCanonical()(get(question).canonical_ref));
                  append($$anchor5, button_89);
                },
                ($$anchor5) => {
                  var p_31 = root_27();
                  append($$anchor5, p_31);
                }
              );
              var p_32 = sibling(node_115, 2);
              var text_138 = only_child(p_32);
              var button_90 = sibling(p_32);
              var button_91 = sibling(button_90);
              reset(div_79);
              template_effect(
                ($0, $1) => {
                  set_text(text_133, (get(homeThread), untrack(() => get(homeThread).title)));
                  set_text(text_134, (get(homeThread), untrack(() => get(homeThread).current_state?.text || get(homeThread).current_state_excerpt || "Chronicle \u6682\u65E0 Current State \u8BB0\u5F55\u3002")));
                  set_text(text_136, `Open Questions \xB7 ${(get(homeThread), untrack(() => get(homeThread).open_question_count)) ?? ""}`);
                  set_text(text_138, `${$0 ?? ""} \xB7 ${$1 ?? ""}`);
                  button_91.disabled = (get(homeThread), untrack(() => !get(homeThread).canonical_ref.obsidian_path));
                },
                [
                  () => (get(homeThread), untrack(() => formatDate(get(homeThread).last_meaningful_change_at))),
                  () => (get(homeThread), untrack(() => get(homeThread).latest_event_title || get(homeThread).latest_event_summary?.slice(0, 100) || "\u6682\u65E0 Event"))
                ]
              );
              event("click", button_90, () => navigate("thread", get(homeThread).thread_id));
              event("click", button_91, () => openRef(get(homeThread).canonical_ref));
              append($$anchor4, div_79);
            };
            var consequent_77 = ($$anchor4) => {
              var fragment_20 = root_110();
              var h3_6 = first_child(fragment_20);
              var text_139 = only_child(h3_6, true);
              var p_33 = sibling(h3_6);
              var text_140 = only_child(p_33, true);
              var p_34 = sibling(p_33);
              var text_141 = only_child(p_34, true);
              var p_35 = sibling(p_34);
              var text_142 = only_child(p_35);
              var button_92 = sibling(p_35);
              var node_116 = sibling(button_92);
              {
                var consequent_76 = ($$anchor5) => {
                  var button_93 = root_109();
                  event("click", button_93, () => showEventMap(get(inspectedEvent)));
                  append($$anchor5, button_93);
                };
                if_block(node_116, ($$render) => {
                  if (get(inspectedEvent), untrack(() => get(inspectedEvent).location_ids?.length)) $$render(consequent_76);
                });
              }
              var button_94 = sibling(node_116);
              template_effect(
                ($0) => {
                  set_text(text_139, (get(inspectedEvent), untrack(() => get(inspectedEvent).title)));
                  set_text(text_140, (get(inspectedEvent), untrack(() => get(inspectedEvent).summary)));
                  set_text(text_141, $0);
                  set_text(text_142, `\u7F6E\u4FE1\u5EA6 ${(get(inspectedEvent), untrack(() => get(inspectedEvent).confidence)) ?? ""} \xB7 ${(get(inspectedEvent), untrack(() => get(inspectedEvent).claim_count)) ?? ""} Claims \xB7 ${(get(inspectedEvent), untrack(() => get(inspectedEvent).source_count)) ?? ""} Sources`);
                },
                [
                  () => (get(inspectedEvent), untrack(() => dateLabel(get(inspectedEvent))))
                ]
              );
              event("click", button_92, () => openEvent(get(inspectedEvent)));
              event("click", button_94, () => focusGraph("event:" + get(inspectedEvent).event_id));
              append($$anchor4, fragment_20);
            };
            var consequent_78 = ($$anchor4) => {
              var fragment_21 = root_111();
              var h3_7 = first_child(fragment_21);
              var text_143 = only_child(h3_7, true);
              var p_36 = sibling(h3_7);
              var text_144 = only_child(p_36);
              var button_95 = sibling(p_36);
              template_effect(() => {
                set_text(text_143, (get(inspectedEntity), untrack(() => get(inspectedEntity).name)));
                set_text(text_144, `${(get(inspectedEntity), untrack(() => get(inspectedEntity).kind)) ?? ""} \xB7 ${(get(inspectedEntity), untrack(() => get(inspectedEntity).thread_count)) ?? ""} Threads \xB7 ${(get(inspectedEntity), untrack(() => get(inspectedEntity).event_count)) ?? ""} Events`);
              });
              event("click", button_95, () => navigate("entity", get(inspectedEntity).entity_id));
              append($$anchor4, fragment_21);
            };
            if_block(node_101, ($$render) => {
              if (get(selectedEdge) && get(page) === "graph") $$render(consequent_64);
              else if (get(selectedNode) && get(page) === "graph") $$render(consequent_71, 1);
              else if (get(selectedLocation) && (get(page) === "map" || get(page) === "thread" && get(threadProjection) === "Map" || get(page) === "entity" && get(entityProjection) === "Map")) $$render(consequent_74, 2);
              else if (get(homeThread) && get(page) === "threads") $$render(consequent_75, 3);
              else if (get(inspectedEvent)) $$render(consequent_77, 4);
              else if (get(inspectedEntity)) $$render(consequent_78, 5);
            });
          }
          reset(aside_1);
          template_effect(() => classes_15 = set_class(aside_1, 1, "wh-inspector", null, classes_15, {
            "wh-home-inspector": get(page) === "threads",
            "wh-inspector-open": get(showInspector)
          }));
          event("click", button_70, () => set(showInspector, false));
          append($$anchor3, aside_1);
        };
        if_block(node_100, ($$render) => {
          if (get(showInspector) || get(page) === "threads") $$render(consequent_79);
        });
      }
      reset(main);
      var footer = sibling(main, 2);
      var text_145 = only_child(footer);
      template_effect(() => set_text(text_145, `Schema ${(deep_read_state(repository()), untrack(() => repository().manifest.schema_version)) ?? ""} \xB7 Generator ${(deep_read_state(repository()), untrack(() => repository().manifest.generator_version)) ?? ""} \xB7 Source ${(deep_read_state(repository()), untrack(() => repository().manifest.source_revision)) ?? ""}`));
      append($$anchor2, fragment);
    };
    if_block(node_11, ($$render) => {
      if (error()) $$render(consequent_3);
      else if (repository()) $$render(consequent_80, 1);
    });
  }
  reset(div);
  bind_this(div, ($$value) => set(appRoot, $$value), () => get(appRoot));
  template_effect(
    ($0, $1, $2, $3) => {
      button_1.disabled = get(historyIndex) <= 0;
      button_2.disabled = (get(historyIndex), get(history), untrack(() => get(historyIndex) >= get(history).length - 1));
      set_value(input, (get(scope), untrack(() => get(scope).search)));
      set_text(text_5, `\u7B5B\u9009 ${get(scopeCount) ? `(${get(scopeCount)})` : ""}`);
      set_text(text_6, `${$0 ?? ""}${$1 ?? ""}${$2 ?? ""}${(get(scope), untrack(() => get(scope).from ? ` \xB7 ${get(scope).from}\u2192${get(scope).to || "\u73B0\u5728"}` : "")) ?? ""}${(get(scope), untrack(() => get(scope).status ? ` \xB7 ${get(scope).status}` : "")) ?? ""}${(get(scope), untrack(() => get(scope).priority ? ` \xB7 ${get(scope).priority}` : "")) ?? ""}`);
      button_7.disabled = !get(scopeCount);
      set_text(text_7, $3);
    },
    [
      () => (get(scope), untrack(() => get(scope).threadId ? threadName(get(scope).threadId) : "\u5168\u5C40\u8BED\u6599")),
      () => (get(scope), untrack(() => get(scope).entityId ? ` \xB7 ${entityName(get(scope).entityId)}` : "")),
      () => (get(scope), deep_read_state(repository()), untrack(() => get(scope).locationId ? ` \xB7 ${repository()?.locationById.get(get(scope).locationId)?.name || get(scope).locationId}` : "")),
      () => (deep_read_state(repository()), untrack(() => repository()?.manifest.generated_at ? `\u751F\u6210 ${formatDate(repository().manifest.generated_at)}` : ""))
    ]
  );
  event("click", button_1, back);
  event("click", button_2, forward);
  event("click", button_3, function(...$$args) {
    refresh()?.apply(this, $$args);
  });
  event("click", button_4, function(...$$args) {
    settings()?.apply(this, $$args);
  });
  event("focus", input, () => set(searchFocused, true));
  event("blur", input, () => set(searchFocused, false));
  event("input", input, (e) => updateSearch(e.currentTarget.value));
  event("click", button_6, () => set(showFilters, !get(showFilters)));
  event("click", button_7, clearScope);
  append($$anchor, div);
  pop();
}

// src/model.ts
var import_node_fs = require("node:fs");
var import_node_crypto = require("node:crypto");
var import_node_path = require("node:path");
var Repository = class _Repository {
  root;
  warning = "";
  graphFault = "";
  manifest;
  threads;
  entities;
  locations;
  threadById;
  entityById;
  locationById;
  _timeline;
  timelinePartitions;
  loadedPartitions = /* @__PURE__ */ new Map();
  _eventById;
  _graphManifest;
  graphBuckets = /* @__PURE__ */ new Map();
  _searchHits;
  _searchIndex;
  static open(output) {
    let pointer = "";
    try {
      pointer = (0, import_node_fs.readFileSync)((0, import_node_path.join)(output, "CURRENT"), "utf8").trim();
      return new _Repository(output, pointer);
    } catch (error) {
      let candidates = [];
      try {
        candidates = (0, import_node_fs.readdirSync)((0, import_node_path.join)(output, "generations")).filter((name) => name !== pointer).sort().reverse();
      } catch {
        throw error;
      }
      for (const candidate of candidates) {
        try {
          const repository = new _Repository(output, candidate);
          repository.warning = `Current generation invalid; using ${candidate}. ${String(error)}`;
          return repository;
        } catch {
          continue;
        }
      }
      throw error;
    }
  }
  constructor(output, pointer) {
    pointer = pointer ?? (0, import_node_fs.readFileSync)((0, import_node_path.join)(output, "CURRENT"), "utf8").trim();
    if (!/^world-historian-dashboard\.v1-0\.7\.[01]-[a-f0-9]{20}$/.test(pointer)) throw Error("Invalid generation pointer");
    this.root = (0, import_node_path.join)(output, "generations", pointer);
    const get3 = (name) => JSON.parse((0, import_node_fs.readFileSync)((0, import_node_path.join)(this.root, name), "utf8"));
    this.manifest = get3("manifest.json");
    if (this.manifest.schema_version !== "world-historian-dashboard.v1") throw Error("Unsupported dashboard schema");
    if (!(0, import_node_fs.existsSync)((0, import_node_path.join)(this.root, "graph-manifest.json")) || !(0, import_node_fs.existsSync)((0, import_node_path.join)(this.root, "timeline-partitions.json"))) throw Error("Incomplete dashboard generation");
    this.timelinePartitions = get3("timeline-partitions.json");
    if (!Array.isArray(this.timelinePartitions) || this.timelinePartitions.reduce((n, p) => n + p.count, 0) !== this.manifest.event_count || this.timelinePartitions.some((p) => !/^(\d{4}-\d{2}|undated)$/.test(p.key) || !Number.isInteger(p.count) || p.count < 0)) throw Error("Invalid timeline partitions");
    const graphManifest = get3("graph-manifest.json");
    if (graphManifest.format !== "sharded-adjacency.v1" || !Array.isArray(graphManifest.buckets) || !Array.isArray(graphManifest.edge_types)) throw Error("Invalid graph manifest");
    this._graphManifest = graphManifest;
    this.threads = get3("threads.json");
    this.entities = get3("entities.json");
    this.locations = get3("locations.json");
    if (this.threads.length !== this.manifest.thread_count || this.entities.length !== this.manifest.entity_count || this.locations.length !== this.manifest.location_count) throw Error("Invalid dashboard generation");
    this.threadById = new Map(this.threads.map((t) => [t.thread_id, t]));
    this.entityById = new Map(this.entities.map((e) => [e.entity_id, e]));
    this.locationById = new Map(this.locations.map((l) => [l.location_id, l]));
  }
  partition(key2) {
    let items = this.loadedPartitions.get(key2);
    if (!items) {
      items = JSON.parse((0, import_node_fs.readFileSync)((0, import_node_path.join)(this.root, "timeline", `${key2}.json`), "utf8"));
      if (items.length !== this.timelinePartitions.find((p) => p.key === key2)?.count) throw Error("Invalid timeline partition");
      this.loadedPartitions.set(key2, items);
    }
    return items;
  }
  recentEvents(limit) {
    const results = [];
    for (const partition of this.timelinePartitions) {
      results.push(...this.partition(partition.key).slice(0, Math.max(0, limit - results.length)));
      if (results.length >= limit) break;
    }
    return results;
  }
  get timeline() {
    if (!this._timeline) {
      this._timeline = this.timelinePartitions.flatMap((p) => this.partition(p.key));
      if (this._timeline.length !== this.manifest.event_count) throw Error("Invalid timeline index");
    }
    return this._timeline;
  }
  get eventById() {
    if (!this._eventById) this._eventById = new Map(this.timeline.map((e) => [e.event_id, e]));
    return this._eventById;
  }
  get graphManifest() {
    if (!this._graphManifest) {
      const value = JSON.parse((0, import_node_fs.readFileSync)((0, import_node_path.join)(this.root, "graph-manifest.json"), "utf8"));
      if (value.format !== "sharded-adjacency.v1") throw Error("Invalid graph format");
      this._graphManifest = value;
    }
    return this._graphManifest;
  }
  bucket(id) {
    const prefix = (0, import_node_crypto.createHash)("sha256").update(id).digest("hex").slice(0, 2);
    let bucket = this.graphBuckets.get(prefix);
    if (!bucket) {
      bucket = JSON.parse((0, import_node_fs.readFileSync)((0, import_node_path.join)(this.root, "graph", `${prefix}.json`), "utf8"));
      if (!bucket?.nodes || !bucket?.adjacency) throw Error("Invalid graph bucket");
      this.graphBuckets.set(prefix, bucket);
      if (this.graphBuckets.size > 24) this.graphBuckets.delete(this.graphBuckets.keys().next().value);
    }
    return bucket;
  }
  graphNode(id) {
    try {
      return this.bucket(id).nodes[id];
    } catch (error) {
      this.graphFault = `Graph bucket could not be read: ${String(error)}`;
      return void 0;
    }
  }
  neighbors(id) {
    try {
      return this.bucket(id).adjacency[id] || [];
    } catch (error) {
      this.graphFault = `Graph bucket could not be read: ${String(error)}`;
      return [];
    }
  }
  graphEdgeTypes() {
    try {
      return this.graphManifest.edge_types;
    } catch (error) {
      this.graphFault = `Graph manifest could not be read: ${String(error)}`;
      return [];
    }
  }
  initSearch() {
    if (this._searchIndex) return;
    this._searchHits = [...this.threads.map((t) => ({ type: "thread", id: t.thread_id, label: t.title, summary: t.latest_event_summary || "" })), ...this.timeline.map((e) => ({ type: "event", id: e.event_id, label: e.title, summary: e.summary })), ...this.entities.map((e) => ({ type: "entity", id: e.entity_id, label: e.name, summary: e.aliases.join(" ") }))];
    this._searchIndex = /* @__PURE__ */ new Map();
    this._searchHits.forEach((hit, index2) => {
      for (const gram of this.grams((hit.label + " " + hit.summary).toLocaleLowerCase())) {
        let set2 = this._searchIndex.get(gram);
        if (!set2) {
          set2 = /* @__PURE__ */ new Set();
          this._searchIndex.set(gram, set2);
        }
        set2.add(index2);
      }
    });
  }
  grams(value) {
    const chars = [...value];
    const grams = /* @__PURE__ */ new Set();
    for (let i = 0; i < chars.length; i++) {
      if (!chars[i].trim()) continue;
      grams.add(chars[i]);
      if (i + 1 < chars.length) grams.add(chars[i] + chars[i + 1]);
    }
    return grams;
  }
  search(query, limit = 20) {
    const normalized = query.trim().toLocaleLowerCase();
    if (!normalized) return [];
    this.initSearch();
    const hits = this._searchHits, index2 = this._searchIndex;
    const grams = [...this.grams(normalized)];
    if (!grams.length) return [];
    grams.sort((a, b) => (index2.get(a)?.size || 0) - (index2.get(b)?.size || 0));
    const first = index2.get(grams[0]);
    if (!first) return [];
    const matches = [];
    for (const number of first) {
      if (grams.every((g) => index2.get(g)?.has(number))) {
        const hit = hits[number];
        if ((hit.label + " " + hit.summary).toLocaleLowerCase().includes(normalized)) matches.push(hit);
      }
    }
    matches.sort((a, b) => Number(b.label.toLocaleLowerCase().startsWith(normalized)) - Number(a.label.toLocaleLowerCase().startsWith(normalized)) || a.label.localeCompare(b.label));
    return matches.slice(0, limit);
  }
  thread(id) {
    return this.detail("threads", id);
  }
  event(id) {
    return this.detail("events", id);
  }
  entity(id) {
    return this.detail("entities", id);
  }
  detail(kind, id) {
    if (!/^[a-z0-9_-]+$/i.test(id)) throw Error("Invalid object ID");
    const path = (0, import_node_path.join)(this.root, kind, `${id}.json`);
    if (!(0, import_node_fs.existsSync)(path)) throw Error(`Missing ${kind} detail: ${id}`);
    return JSON.parse((0, import_node_fs.readFileSync)(path, "utf8"));
  }
  matchesEvent(e, scope) {
    const date = e.occurred_at || e.reported_at || e.first_observed_at || "";
    return (!scope.from || date >= scope.from) && (!scope.to || date.slice(0, 10) <= scope.to) && (!scope.threadId || e.thread_ids.includes(scope.threadId)) && (!scope.entityId || e.entity_ids.includes(scope.entityId)) && (!scope.locationId || e.location_ids.includes(scope.locationId)) && (!scope.claimState || e.claim_states.includes(scope.claimState)) && (!scope.status && !scope.priority || e.thread_ids.some((id) => {
      const thread = this.threadById.get(id);
      return thread && (!scope.status || thread.status === scope.status) && (!scope.priority || thread.priority === scope.priority);
    })) && (!scope.search || (e.title + " " + e.summary).toLocaleLowerCase().includes(scope.search.toLocaleLowerCase()));
  }
  filteredEvents(scope) {
    const partitions = scope.from || scope.to ? this.timelinePartitions.filter((p) => p.key === "undated" || (!scope.from || p.key >= scope.from.slice(0, 7)) && (!scope.to || p.key <= scope.to.slice(0, 7))) : this.timelinePartitions;
    return partitions.flatMap((p) => this.partition(p.key)).filter((e) => this.matchesEvent(e, scope));
  }
  filteredThreads(scope) {
    const needsEvents = Boolean(scope.from || scope.to || scope.claimState);
    const visibleThreadIds = needsEvents ? new Set(this.filteredEvents({ ...scope, search: "" }).flatMap((e) => e.thread_ids)) : null;
    return this.threads.filter((t) => (!scope.status || t.status === scope.status) && (!scope.priority || t.priority === scope.priority) && (!scope.threadId || t.thread_id === scope.threadId) && (!scope.entityId || this.entityById.get(scope.entityId)?.thread_ids.includes(t.thread_id)) && (!scope.locationId || t.location_ids.includes(scope.locationId)) && (!visibleThreadIds || visibleThreadIds.has(t.thread_id)) && (!scope.search || (t.title + " " + (t.latest_event_summary || "")).toLocaleLowerCase().includes(scope.search.toLocaleLowerCase())));
  }
  filteredEntities(scope) {
    const needsEvents = Boolean(scope.from || scope.to || scope.locationId || scope.claimState || scope.status || scope.priority);
    const visible = needsEvents ? new Set(this.filteredEvents({ ...scope, search: "" }).flatMap((e) => e.entity_ids)) : null;
    return this.entities.filter((e) => (!scope.search || (e.name + " " + e.aliases.join(" ")).toLocaleLowerCase().includes(scope.search.toLocaleLowerCase())) && (!scope.threadId || e.thread_ids.includes(scope.threadId)) && (!visible || visible.has(e.entity_id)));
  }
};

// src/main.ts
var VIEW_TYPE = "world-historian-dashboard";
var defaults = { database: "", output: "", projector: "", pythonExecutable: process.platform === "win32" ? "python" : "python3", noteIndex: "", locationRegistry: "" };
var DashboardView = class extends import_obsidian.ItemView {
  plugin;
  component = null;
  constructor(leaf, plugin) {
    super(leaf);
    this.plugin = plugin;
  }
  getViewType() {
    return VIEW_TYPE;
  }
  getDisplayText() {
    return "World Historian Dashboard";
  }
  getIcon() {
    return "network";
  }
  async onOpen() {
    await this.render();
  }
  async onClose() {
    if (this.component) {
      await unmount(this.component);
      this.component = null;
    }
  }
  async render() {
    if (this.component) {
      await unmount(this.component);
      this.component = null;
    }
    const root6 = this.contentEl;
    root6.empty();
    root6.addClass("wh-dashboard-host");
    let repository = null;
    let error = "";
    let stale = false;
    try {
      repository = Repository.open(this.plugin.settings.output);
      try {
        stale = (0, import_node_fs2.statSync)(this.plugin.settings.database).mtimeMs > Date.parse(repository.manifest.generated_at);
      } catch {
        repository.warning = repository.warning || "Chronicle database is unavailable; showing cached generation";
      }
    } catch (e) {
      error = String(e);
    }
    try {
      this.component = mount(Dashboard, { target: root6, props: {
        repository,
        error,
        stale,
        refresh: () => this.plugin.refreshAndRender(),
        openNote: (path) => this.plugin.openNote(path),
        openCanonical: (ref) => this.plugin.openCanonical(ref),
        searchAll: this.plugin.settings.projector ? (query) => this.plugin.search(query) : void 0,
        settings: () => this.plugin.openSettings()
      } });
    } catch (cause) {
      root6.textContent = `World Historian Dashboard failed to open: ${String(cause)}`;
      root6.addClass("wh-alert");
      console.error("World Historian Dashboard failed to mount", cause);
    }
  }
};
var HistorianPlugin = class extends import_obsidian.Plugin {
  settings = defaults;
  async onload() {
    this.settings = Object.assign({}, defaults, await this.loadData());
    this.registerView(VIEW_TYPE, (leaf) => new DashboardView(leaf, this));
    this.addRibbonIcon("network", "World Historian Dashboard", () => void this.activate());
    this.addCommand({ id: "open-dashboard", name: "Open dashboard", callback: () => void this.activate() });
    this.addCommand({ id: "refresh-dashboard", name: "Refresh read model", callback: () => void this.refreshAndRender() });
    this.addSettingTab(new DashboardSettings(this.app, this));
  }
  async activate() {
    let leaf = this.app.workspace.getLeavesOfType(VIEW_TYPE)[0];
    if (!leaf) {
      leaf = this.app.workspace.getLeaf("tab");
      await leaf.setViewState({ type: VIEW_TYPE, active: true });
    }
    await this.app.workspace.revealLeaf(leaf);
  }
  async refresh() {
    if (!this.settings.database || !this.settings.output || !this.settings.projector) throw Error("Configure database, output and projector paths in plugin settings");
    const args = [this.settings.projector, "--db", this.settings.database, "--output", this.settings.output];
    if (this.settings.noteIndex) args.push("--note-index", this.settings.noteIndex);
    if (this.settings.locationRegistry) args.push("--location-registry", this.settings.locationRegistry);
    if (this.app.vault.adapter instanceof import_obsidian.FileSystemAdapter) args.push("--vault", this.app.vault.adapter.getBasePath());
    await new Promise((resolve, reject) => (0, import_node_child_process.execFile)(this.settings.pythonExecutable, args, { timeout: 18e5, maxBuffer: 1024 * 1024 }, (error, stdout, stderr) => error ? reject(new Error(stderr || error.message)) : resolve()));
    new import_obsidian.Notice("World Historian read model refreshed");
  }
  async refreshAndRender() {
    try {
      await this.refresh();
      for (const leaf of this.app.workspace.getLeavesOfType(VIEW_TYPE)) await leaf.view.render();
    } catch (e) {
      new import_obsidian.Notice(`Refresh failed: ${String(e)}`, 1e4);
    }
  }
  async search(query) {
    if (!this.settings.projector || !this.settings.output) return [];
    const args = [this.settings.projector, "--output", this.settings.output, "--search-query", query];
    const raw = await new Promise((resolve, reject) => (0, import_node_child_process.execFile)(this.settings.pythonExecutable, args, { timeout: 15e3, maxBuffer: 256 * 1024 }, (error, stdout, stderr) => error ? reject(new Error(stderr || error.message)) : resolve(stdout)));
    return JSON.parse(raw);
  }
  async openNote(path) {
    const file = this.app.vault.getFileByPath(path);
    if (file) await this.app.workspace.getLeaf("tab").openFile(file);
    else new import_obsidian.Notice(`Note missing: ${path}`);
  }
  async openCanonical(ref) {
    if (ref.kind !== "chronicle" || !ref.table || !ref.id) {
      new import_obsidian.Notice("Canonical record is unavailable");
      return;
    }
    try {
      const args = [this.settings.projector, "--db", this.settings.database, "--inspect-table", ref.table, "--inspect-id", ref.id];
      const raw = await new Promise((resolve, reject) => (0, import_node_child_process.execFile)(this.settings.pythonExecutable, args, { timeout: 15e3, maxBuffer: 256 * 1024 }, (error, stdout, stderr) => error ? reject(new Error(stderr || error.message)) : resolve(stdout)));
      const modal = new import_obsidian.Modal(this.app);
      modal.titleEl.setText(`${ref.table} \xB7 ${ref.id}`);
      modal.contentEl.createEl("pre", { text: JSON.stringify(JSON.parse(raw).record, null, 2) });
      modal.contentEl.addClass("wh-canonical-record");
      modal.open();
    } catch (e) {
      new import_obsidian.Notice(`Could not open canonical record: ${String(e)}`, 1e4);
    }
  }
  openSettings() {
    this.app.setting.open();
    this.app.setting.openTabById(this.manifest.id);
  }
};
var DashboardSettings = class extends import_obsidian.PluginSettingTab {
  plugin;
  constructor(app, plugin) {
    super(app, plugin);
    this.plugin = plugin;
  }
  display() {
    const el = this.containerEl;
    el.empty();
    el.createEl("h2", { text: "World Historian Dashboard" });
    for (const [key2, label] of [["database", "Chronicle SQLite file"], ["output", "Dashboard read model directory"], ["projector", "Projector script"], ["pythonExecutable", "Python executable"], ["noteIndex", "Obsidian thread note index"], ["locationRegistry", "Location registry JSON (optional)"]]) {
      new import_obsidian.Setting(el).setName(label).addText((text2) => text2.setValue(this.plugin.settings[key2]).onChange(async (value) => {
        this.plugin.settings[key2] = value;
        await this.plugin.saveData(this.plugin.settings);
      }));
    }
    new import_obsidian.Setting(el).setName("Refresh").addButton((button) => button.setButtonText("Build read model").onClick(() => void this.plugin.refreshAndRender()));
  }
};
