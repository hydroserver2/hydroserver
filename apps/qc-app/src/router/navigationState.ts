import { ref } from 'vue'

/** True from the leave guard asking the user until its navigation lands or
 *  is cancelled. Replacing the route then would cancel that navigation, so
 *  writers of the URL wait. */
export const isLeavingPage = ref(false)
