type NavbarLogo = {
  src: string // File location of the image you want to use
  width: string // Adjust bigger or smaller to make your logo fit
  route?: string // Use if you want to route to an internal page
  link?: string // Use if you want to route to an external page
  target?: string // '_blank' will open page in a new tab. Don't use if you want to use the same tab
}

import logo from '@/assets/hydroserver-icon-min.png'

export const navbarLogo: NavbarLogo = {
  src: logo,
  width: '10rem',
  route: '/browse',
  // link: 'https://hydroserver.org',
  //   target: '_blank',
}
