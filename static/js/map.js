(function () {
  "use strict";

  var TASHKENT = [41.38, 69.29];
  var markers = {};
  var searchQuery = "";
  var loadTimer = null;
  var map;

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
        window.location.href = "/about/" + center.id + "/";
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
