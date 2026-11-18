(function () {
  "use strict";

  var TASHKENT = [41.38, 69.29];
  var markers = {};
  var searchQuery = "";
  var loadTimer = null;
  var map;
  var centerSheet;
  var centerSheetPanel;
  var centerSheetTitle;
  var centerSheetBody;
  var centerSheetFooter;
  var centerSheetDrag;
  var centerSheetClose;
  var previousBodyOverflow = "";
  var dragState = null;

  function esc(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch];
    });
  }

  function fullPrice(value) {
    return value == null ? "" : Number(value).toLocaleString("ru-RU");
  }

  function priceText(center) {
    var min = center.price_min != null ? center.price_min : center.price_monthly;
    var max = center.price_max != null ? center.price_max : center.price_monthly;
    if (min != null && max != null) return fullPrice(min) + " - " + fullPrice(max) + " UZS";
    if (min != null) return fullPrice(min) + " UZS";
    return "Narx ko'rsatilmagan";
  }

  function safeHttpUrl(value) {
    if (!value) return "";
    try {
      var url = new URL(value, window.location.origin);
      return url.protocol === "http:" || url.protocol === "https:" ? url.href : "";
    } catch (error) {
      return "";
    }
  }

  function coursePrice(course) {
    var min = course.price_min;
    var max = course.price_max;
    if (min != null && max != null) return fullPrice(min) + " - " + fullPrice(max) + " UZS";
    if (min != null) return fullPrice(min) + " UZS";
    if (max != null) return fullPrice(max) + " UZS";
    return "";
  }

  function renderCenterSheet(center) {
    var imageUrl = safeHttpUrl(center.image_url);
    if (!imageUrl && center.images && center.images.length) {
      imageUrl = safeHttpUrl(center.images[0].image);
    }

    var cover = imageUrl
      ? '<img class="center-sheet__cover" src="' + esc(imageUrl) + '" alt="' + esc(center.name) + '">'
      : '<div class="center-sheet__cover center-sheet__placeholder" aria-hidden="true"><span class="material-symbols-outlined">school</span></div>';
    var rating = Number(center.rating) > 0
      ? '<div class="center-sheet__rating">★ ' + esc(Number(center.rating).toFixed(1)) + '</div>'
      : "";
    var subjects = (center.subjects || []).map(function (subject) {
      return subject && subject.name ? '<span class="center-sheet__chip">' + esc(subject.name) + '</span>' : "";
    }).join("");
    var courses = (center.courses || []).map(function (course) {
      if (!course || !course.name) return "";
      var category = course.category && course.category.name ? " · " + esc(course.category.name) : "";
      var price = coursePrice(course);
      return '<div class="center-sheet__course"><span class="center-sheet__course-name">' +
        esc(course.name) + category + '</span>' +
        (price ? '<span class="center-sheet__course-price">' + esc(price) + '</span>' : "") +
        '</div>';
    }).join("");
    var description = center.description
      ? '<p class="center-sheet__description">' + esc(center.description) + '</p>'
      : "";
    var website = safeHttpUrl(center.website);
    var websiteLink = website
      ? '<p class="center-sheet__description"><a href="' + esc(website) + '" target="_blank" rel="noopener noreferrer">Veb-saytni ochish</a></p>'
      : "";
    var phone = String(center.phone || "").trim();
    var phoneHref = phone.replace(/[^\d+]/g, "");

    centerSheetTitle.textContent = center.name || "O'quv markazi";
    centerSheetBody.innerHTML =
      '<div class="center-sheet__overview">' + cover +
        '<div class="min-w-0"><p class="center-sheet__address">' + esc(center.address || "Manzil ko'rsatilmagan") + '</p>' +
          '<p class="center-sheet__address">' + esc(priceText(center)) + '</p>' + rating +
        '</div>' +
      '</div>' +
      description +
      (subjects ? '<h3 class="center-sheet__section-title">Yo\'nalishlar</h3><div class="center-sheet__chips">' + subjects + '</div>' : "") +
      (courses ? '<h3 class="center-sheet__section-title">Kurslar</h3>' + courses : "") +
      websiteLink;

    centerSheetFooter.innerHTML =
      (phoneHref ? '<a class="center-sheet__action center-sheet__action--secondary" href="tel:' + esc(phoneHref) + '">' +
        '<span class="material-symbols-outlined">call</span>Qo\'ng\'iroq</a>' : "") +
      '<a class="center-sheet__action center-sheet__action--primary" href="/about/' +
        encodeURIComponent(center.id) + '/">Batafsil</a>';
  }

  function openCenterSheet(center) {
    var wasOpen = centerSheet.classList.contains("is-open");
    renderCenterSheet(center);
    if (!wasOpen) {
      centerSheetPanel.style.height = "";
      previousBodyOverflow = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      centerSheet.classList.add("is-open");
      centerSheet.setAttribute("aria-hidden", "false");
      centerSheetDrag.setAttribute("aria-expanded", "true");
    }
    centerSheetClose.focus();
  }

  function closeCenterSheet() {
    if (!centerSheet.classList.contains("is-open")) return;
    centerSheet.classList.remove("is-open");
    centerSheet.setAttribute("aria-hidden", "true");
    centerSheetDrag.setAttribute("aria-expanded", "false");
    document.body.style.overflow = previousBodyOverflow;
  }

  function setupCenterSheet() {
    centerSheet = document.getElementById("center-sheet");
    centerSheetPanel = document.getElementById("center-sheet-panel");
    centerSheetTitle = document.getElementById("center-sheet-title");
    centerSheetBody = document.getElementById("center-sheet-body");
    centerSheetFooter = document.getElementById("center-sheet-footer");
    centerSheetDrag = document.getElementById("center-sheet-drag");
    centerSheetClose = document.getElementById("center-sheet-close");

    document.getElementById("center-sheet-backdrop").addEventListener("click", closeCenterSheet);
    centerSheetClose.addEventListener("click", closeCenterSheet);
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") closeCenterSheet();
    });

    centerSheetDrag.addEventListener("pointerdown", function (event) {
      if (!event.isPrimary || (event.pointerType === "mouse" && event.button !== 0)) return;
      dragState = {
        pointerId: event.pointerId,
        startY: event.clientY,
        startHeight: centerSheetPanel.getBoundingClientRect().height,
        deltaY: 0
      };
      centerSheetPanel.classList.add("is-dragging");
      centerSheetDrag.setPointerCapture(event.pointerId);
      event.preventDefault();
    });
    centerSheetDrag.addEventListener("pointermove", function (event) {
      if (!dragState || event.pointerId !== dragState.pointerId) return;
      dragState.deltaY = event.clientY - dragState.startY;
      var minHeight = Math.min(280, window.innerHeight * 0.35);
      var maxHeight = window.innerHeight * 0.86;
      var height = Math.max(minHeight, Math.min(maxHeight, dragState.startHeight - dragState.deltaY));
      centerSheetPanel.style.height = Math.round(height) + "px";
    });
    function finishSheetDrag(event) {
      if (!dragState || event.pointerId !== dragState.pointerId) return;
      var deltaY = dragState.deltaY;
      dragState = null;
      centerSheetPanel.classList.remove("is-dragging");
      if (deltaY > Math.max(120, window.innerHeight * 0.18)) {
        closeCenterSheet();
      } else if (deltaY < -60) {
        centerSheetPanel.style.height = Math.round(window.innerHeight * 0.86) + "px";
      } else {
        centerSheetPanel.style.height = "56dvh";
      }
    }
    centerSheetDrag.addEventListener("pointerup", finishSheetDrag);
    centerSheetDrag.addEventListener("pointercancel", finishSheetDrag);
    centerSheetDrag.addEventListener("keydown", function (event) {
      if (event.key === "ArrowUp") {
        event.preventDefault();
        centerSheetPanel.style.height = Math.round(window.innerHeight * 0.86) + "px";
      } else if (event.key === "ArrowDown") {
        event.preventDefault();
        if (centerSheetPanel.getBoundingClientRect().height > window.innerHeight * 0.65) {
          centerSheetPanel.style.height = "56dvh";
        } else {
          closeCenterSheet();
        }
      }
    });
  }

  async function api(path, params) {
    var query = new URLSearchParams(params || {}).toString();
    var response = await fetch("/api/" + path + "/" + (query ? "?" + query : ""));
    if (!response.ok) throw new Error("API " + response.status);
    return response.json();
  }

  function visibleBounds() {
    if (!map) return null;
    var bounds = map.getBounds();
    var sw = bounds[0];
    var ne = bounds[1];
    return {
      south: sw[0].toFixed(7),
      west: sw[1].toFixed(7),
      north: ne[0].toFixed(7),
      east: ne[1].toFixed(7)
    };
  }

  function clearMarkers() {
    Object.keys(markers).forEach(function (id) {
      map.geoObjects.remove(markers[id]);
    });
    markers = {};
  }

  function renderMarkers(list) {
    clearMarkers();
    list.forEach(function (center) {
      if (!isFinite(center.latitude) || !isFinite(center.longitude)) return;
      var marker = new ymaps.Placemark(
        [center.latitude, center.longitude],
        {
          hintContent: center.name,
          iconContent: esc(center.name + " · " + priceText(center))
        },
        {
          preset: "islands#yellowStretchyIcon",
          cursor: "pointer",
          openBalloonOnClick: false
        }
      );
      function openCenter() {
        openCenterSheet(center);
      }
      marker.events.add("click", openCenter);
      marker.events.add("tap", openCenter);
      map.geoObjects.add(marker);
      markers[center.id] = marker;
    });
  }

  async function loadVisibleCenters() {
    var bounds = visibleBounds();
    if (!bounds) return;
    try {
      var params = Object.assign({}, bounds, searchQuery ? { q: searchQuery } : {});
      var list = await api("centers", params);
      renderMarkers(list);
      document.getElementById("count-pill").textContent = list.length + " ta markaz";
      document.getElementById("count-pill").classList.remove("hidden");
    } catch (error) {
      console.error(error);
    }
  }

  function scheduleLoad() {
    clearTimeout(loadTimer);
    loadTimer = setTimeout(loadVisibleCenters, 250);
  }

  document.addEventListener("DOMContentLoaded", function () {
    setupCenterSheet();
    ymaps.ready(function () {
      map = new ymaps.Map("map", {
        center: TASHKENT,
        zoom: 11,
        controls: []
      }, { suppressMapOpenBlock: true });

      map.events.add("boundschange", scheduleLoad);

      document.getElementById("locate-btn").addEventListener("click", function () {
        if (!navigator.geolocation) return;
        navigator.geolocation.getCurrentPosition(function (pos) {
          var coords = [pos.coords.latitude, pos.coords.longitude];
          map.setCenter(coords, 14);
          var marker = new ymaps.Placemark(coords, {}, {
            preset: "islands#blueCircleDotIcon",
            iconShape: null
          });
          map.geoObjects.add(marker);
        });
      });

      document.getElementById("zoom-in").addEventListener("click", function () { map.setZoom(map.getZoom() + 1); });
      document.getElementById("zoom-out").addEventListener("click", function () { map.setZoom(map.getZoom() - 1); });

      var form = document.getElementById("search-form");
      var input = document.getElementById("search-input");
      form.addEventListener("submit", function (event) {
        event.preventDefault();
        searchQuery = input.value.trim();
        loadVisibleCenters();
      });
      document.getElementById("clear-btn").addEventListener("click", function () {
        input.value = "";
        searchQuery = "";
        loadVisibleCenters();
      });

      document.getElementById("nav-map").addEventListener("click", function () {
        loadVisibleCenters();
      });
      document.getElementById("nav-saved").addEventListener("click", function () {
        window.location.href = "/";
      });

      loadVisibleCenters();
    });
  });
})();
