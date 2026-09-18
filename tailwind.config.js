/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/templates/**/*.html",
    "./app/static/js/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        'ceiba-yellow':      'var(--brand-yellow)',
        'ceiba-yellow-dark': 'var(--brand-yellow-dark)',
        'ceiba-black':       'var(--brand-black)',
        'ceiba-dark':        'var(--brand-black-light)',
      }
    }
  },
  plugins: [],
}
