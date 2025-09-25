/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#165DFF',
        success: '#52C41A',
        warning: '#FAAD14',
        danger: '#FF4D4F',
        dark: '#1D2129',
        'dark-2': '#4E5969',
        'light-1': '#F2F3F5',
        'light-2': '#E5E6EB',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
