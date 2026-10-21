'use strict';
// Progressive enhancement only. Navigation and search remain functional without JavaScript.
for(const link of document.querySelectorAll('.navlinks a')){
 if(link.getAttribute('href')===location.pathname)link.setAttribute('aria-current','page');
}
