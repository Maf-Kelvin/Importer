// Applies the saved light/dark choice before the first paint, so the page does not flash.
// A separate file (not inline) because the Content-Security-Policy allows scripts from our own origin only.
try {
  var t = localStorage.getItem('theme');
  if (t === 'dark' || (!t && matchMedia('(prefers-color-scheme: dark)').matches)) document.documentElement.classList.add('dark');
} catch (e) {}
