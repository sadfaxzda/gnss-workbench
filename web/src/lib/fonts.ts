let readiness: Promise<unknown> | undefined

// Canvas must measure text after the same faces used by HTML/SVG have loaded.
// Other developers' machines may not have these local fonts; keep the app usable.
export function loadWorkbenchFonts() {
  readiness ??= Promise.allSettled(
    [400, 700].flatMap((weight) =>
      ['GNSS 0123456789', '卫星定位，中文。'].map((sample) =>
        document.fonts.load(`${weight} 14px "GNSS Course Font"`, sample),
      ),
    ),
  ).then((results) => {
    const loaded = (index: number) => {
      const result = results[index]
      return result.status === 'fulfilled' && result.value.length > 0
    }
    document.documentElement.dataset.fontLatin = loaded(0) && loaded(2) ? 'ready' : 'fallback'
    document.documentElement.dataset.fontChinese = loaded(1) && loaded(3) ? 'ready' : 'fallback'
    return results
  })
  return readiness
}
