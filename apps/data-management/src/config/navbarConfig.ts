type NavbarLogo = {
  src: string // File location of the image you want to use
  route?: string // Use if you want to route to an internal page
  link?: string // Use if you want to route to an external page
  target?: string // '_blank' will open page in a new tab. Don't use if you want to use the same tab
}

import logo from '@/assets/icon-color-thick.svg'

export const navbarLogo: NavbarLogo = {
  src: logo,
  route: '/browse',
  // link: 'https://hydroserver.org',
  //   target: '_blank',
}
