/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { computed, ref, watch } from 'vue';
const props = withDefaults(defineProps(), {
    theme: 'auto',
    title: '',
    logo: '',
    sponsorsUrl: '',
    height: 180,
});
const emit = defineEmits();
const codeRef = ref(null);
const copied = ref(false);
const open = computed(() => props.modelValue);
function close() { emit('update:modelValue', false); }
const embedUrl = computed(() => {
    const origin = window.location.origin;
    // If you’re using Vue Router hash mode (default in many Vite templates)
    const base = origin + '/#';
    const path = `/embed/scoreboard/${encodeURIComponent(props.gameId)}`;
    const qs = new URLSearchParams();
    if (props.theme && props.theme !== 'auto')
        qs.set('theme', props.theme);
    if (props.title)
        qs.set('title', props.title);
    if (props.logo)
        qs.set('logo', props.logo);
    if (props.sponsorsUrl)
        qs.set('sponsorsUrl', props.sponsorsUrl);
    // You can expose sponsorClickable/rotateMs here later if needed.
    const q = qs.toString();
    return q ? `${base}${path}?${q}` : `${base}${path}`;
});
const iframeCode = computed(() => {
    // width 100% so it fits host, fixed height to avoid reflow
    return `<iframe src="${embedUrl.value}" width="100%" height="${props.height}" frameborder="0" scrolling="no" allowtransparency="true"></iframe>`;
});
async function copy() {
    const txt = iframeCode.value;
    try {
        // Primary (modern)
        await navigator.clipboard.writeText(txt);
        copied.value = true;
    }
    catch {
        // Fallback (mobile Safari etc.)
        if (codeRef.value) {
            codeRef.value.focus();
            codeRef.value.select();
            try {
                document.execCommand('copy');
            }
            catch {
                // ignore legacy clipboard failures; fall through to label reset
            }
            copied.value = true;
        }
    }
    // Reset label after a moment
    window.setTimeout(() => (copied.value = false), 1600);
}
watch(open, (o) => {
    if (o)
        setTimeout(() => codeRef.value?.select(), 50);
});
const __VLS_defaults = {
    theme: 'auto',
    title: '',
    logo: '',
    sponsorsUrl: '',
    height: 180,
};
const __VLS_ctx = {
    ...{},
    ...{},
    ...{},
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['hdr']} */ ;
/** @type {__VLS_StyleScopedClasses['ftr']} */ ;
/** @type {__VLS_StyleScopedClasses['hdr']} */ ;
/** @type {__VLS_StyleScopedClasses['note']} */ ;
/** @type {__VLS_StyleScopedClasses['primary']} */ ;
/** @type {__VLS_StyleScopedClasses['preview']} */ ;
/** @type {__VLS_StyleScopedClasses['card']} */ ;
/** @type {__VLS_StyleScopedClasses['code']} */ ;
/** @type {__VLS_StyleScopedClasses['x']} */ ;
/** @type {__VLS_StyleScopedClasses['note']} */ ;
/** @type {__VLS_StyleScopedClasses['preview']} */ ;
if (__VLS_ctx.open) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ onClick: (__VLS_ctx.close) },
        ...{ class: "backdrop" },
    });
    /** @type {__VLS_StyleScopedClasses['backdrop']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "card" },
        role: "dialog",
        'aria-modal': "true",
        'aria-labelledby': "share-title",
    });
    /** @type {__VLS_StyleScopedClasses['card']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({
        ...{ class: "hdr" },
    });
    /** @type {__VLS_StyleScopedClasses['hdr']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({
        id: "share-title",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.close) },
        ...{ class: "x" },
        'aria-label': "Close",
    });
    /** @type {__VLS_StyleScopedClasses['x']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
        ...{ class: "body" },
    });
    /** @type {__VLS_StyleScopedClasses['body']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "lbl" },
    });
    /** @type {__VLS_StyleScopedClasses['lbl']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "code-wrap" },
    });
    /** @type {__VLS_StyleScopedClasses['code-wrap']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.textarea, __VLS_intrinsics.textarea)({
        ref: "codeRef",
        ...{ class: "code" },
        readonly: true,
        value: (__VLS_ctx.iframeCode),
        'aria-label': "Embed code",
    });
    /** @type {__VLS_StyleScopedClasses['code']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.copy) },
        ...{ class: "copy" },
    });
    /** @type {__VLS_StyleScopedClasses['copy']} */ ;
    (__VLS_ctx.copied ? 'Copied!' : 'Copy');
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "note" },
    });
    /** @type {__VLS_StyleScopedClasses['note']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.code, __VLS_intrinsics.code)({});
    (__VLS_ctx.height);
    __VLS_asFunctionalElement1(__VLS_intrinsics.footer, __VLS_intrinsics.footer)({
        ...{ class: "ftr" },
    });
    /** @type {__VLS_StyleScopedClasses['ftr']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.a, __VLS_intrinsics.a)({
        ...{ class: "preview" },
        href: (__VLS_ctx.embedUrl),
        target: "_blank",
        rel: "noopener",
    });
    /** @type {__VLS_StyleScopedClasses['preview']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.copy) },
        ...{ class: "primary" },
    });
    /** @type {__VLS_StyleScopedClasses['primary']} */ ;
    (__VLS_ctx.copied ? 'Copied!' : 'Copy embed');
}
// @ts-ignore
[open, close, close, iframeCode, copy, copy, copied, copied, height, embedUrl,];
const __VLS_export = (await import('vue')).defineComponent({
    __typeEmits: {},
    __defaults: __VLS_defaults,
    __typeProps: {},
});
export default {};
