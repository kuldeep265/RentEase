/**
 * RentEase — main.js
 * Modern luxury real estate interactivity.
 */

// Search tab toggle (Buy / Rent)
window.setSearchTab = function (mode) {
  const buyTab = document.getElementById('tab-buy');
  const rentTab = document.getElementById('tab-rent');
  const locInput = document.getElementById('hero-location');

  if (mode === 'buy') {
    if (buyTab) buyTab.classList.add('active');
    if (rentTab) rentTab.classList.remove('active');
    if (locInput) locInput.placeholder = "Search luxury villas, penthouses, estates…";
  } else {
    if (rentTab) rentTab.classList.add('active');
    if (buyTab) buyTab.classList.remove('active');
    if (locInput) locInput.placeholder = "City, neighbourhood, or landmark…";
  }
};

document.addEventListener('DOMContentLoaded', function () {

  // ---- Auto-dismiss Django messages after 5 seconds ----
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(function (alert) {
    setTimeout(function () {
      alert.style.transition = 'opacity 0.5s, transform 0.5s';
      alert.style.opacity = '0';
      alert.style.transform = 'translateX(110%)';
      setTimeout(function () { alert.remove(); }, 500);
    }, 5000);

    // Manual close button
    const closeBtn = alert.querySelector('.alert-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', function () {
        alert.style.transition = 'opacity 0.3s';
        alert.style.opacity = '0';
        setTimeout(function () { alert.remove(); }, 300);
      });
    }
  });

  // ---- Sticky navbar shadow on scroll ----
  const navbar = document.querySelector('.navbar');
  if (navbar) {
    window.addEventListener('scroll', function () {
      if (window.scrollY > 15) {
        navbar.classList.add('scrolled');
      } else {
        navbar.classList.remove('scrolled');
      }
    });
  }

  // ---- Mobile nav toggle ----
  const navToggle = document.querySelector('.nav-toggle');
  const navMenu = document.querySelector('.navbar-nav');
  const navActions = document.querySelector('.navbar-actions');

  if (navToggle) {
    navToggle.addEventListener('click', function () {
      navMenu.classList.toggle('open');
      navActions && navActions.classList.toggle('open');
      // Animate hamburger lines
      const spans = navToggle.querySelectorAll('span');
      if (navMenu.classList.contains('open')) {
        spans[0].style.transform = 'rotate(45deg) translate(5px, 5px)';
        spans[1].style.opacity = '0';
        spans[2].style.transform = 'rotate(-45deg) translate(5px, -5px)';
      } else {
        spans[0].style.transform = '';
        spans[1].style.opacity = '';
        spans[2].style.transform = '';
      }
    });
  }

  // ---- Delete confirmation ----
  document.querySelectorAll('[data-confirm]').forEach(function (el) {
    el.addEventListener('click', function (e) {
      var msg = el.getAttribute('data-confirm') || 'Are you sure you want to proceed?';
      if (!confirm(msg)) {
        e.preventDefault();
      }
    });
  });

  // ---- Set today's date as min on date inputs ----
  document.querySelectorAll('input[type="date"]').forEach(function (input) {
    if (!input.min) {
      var today = new Date().toISOString().split('T')[0];
      input.min = today;
    }
  });

  // ---- Smooth scroll for anchor links ----
  document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
    anchor.addEventListener('click', function (e) {
      var target = document.querySelector(this.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  // ---- Property image lazy loading fallback ----
  document.querySelectorAll('img[data-src]').forEach(function (img) {
    img.src = img.dataset.src;
  });

});
