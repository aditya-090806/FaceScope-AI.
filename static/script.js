document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("imageInput");
  const label = document.getElementById("fileLabel");
  const preview = document.getElementById("imagePreview");
  if (input) input.addEventListener("change", () => {
    const file = input.files && input.files[0];
    if (!file) return;
    label.textContent = file.name;
    preview.src = URL.createObjectURL(file);
    preview.hidden = false;
  });

  const video = document.getElementById("cameraVideo");
  const placeholder = document.getElementById("cameraPlaceholder");
  const start = document.getElementById("startCamera");
  const capture = document.getElementById("captureCamera");
  const message = document.getElementById("cameraMessage");
  let stream = null;
  if (start && video && capture) {
    start.addEventListener("click", async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({video: {facingMode: "user"}, audio: false});
        video.srcObject = stream;
        video.hidden = false;
        placeholder.hidden = true;
        capture.disabled = false;
        start.textContent = "Camera enabled";
        message.textContent = "Camera is active. Capture when ready.";
      } catch (e) {
        message.textContent = "Camera access was unavailable. Allow camera permission or use image upload.";
      }
    });
    capture.addEventListener("click", () => {
      if (!stream || !video.videoWidth) return;
      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      canvas.getContext("2d").drawImage(video, 0, 0);
      canvas.toBlob(blob => {
        if (!blob) { message.textContent = "Could not capture the frame. Try again."; return; }
        const form = new FormData();
        form.append("image", blob, "camera-capture.jpg");
        capture.disabled = true;
        capture.textContent = "Analyzing…";
        fetch("/camera", {method: "POST", body: form, redirect: "follow"})
          .then(r => r.text())
          .then(html => { document.open(); document.write(html); document.close(); })
          .catch(() => { message.textContent = "Request failed. Try image upload instead."; capture.disabled = false; capture.textContent = "Capture & analyze"; });
        stream.getTracks().forEach(track => track.stop());
      }, "image/jpeg", 0.92);
    });
    window.addEventListener("beforeunload", () => { if (stream) stream.getTracks().forEach(t => t.stop()); });
  }

  // Each detected face has its own canvas and its own score data.
  // A single shared canvas ID/data object caused charts after Face 1 to remain blank.
  document.querySelectorAll("canvas.score-chart").forEach((el) => {
    if (typeof Chart === "undefined") return;
    try {
      const scores = JSON.parse(el.dataset.scores || "{}");
      const labels = Object.keys(scores);
      const values = labels.map(label => Number(scores[label]) || 0);
      if (!labels.length) return;
      new Chart(el, {
        type: "bar",
        data: {labels, datasets: [{label: "Model score (%)", data: values, backgroundColor: "#62e6dccc", borderRadius: 5}]},
        options: {indexAxis: "y", responsive: true, maintainAspectRatio: true, plugins: {legend: {display: false}}, scales: {x: {beginAtZero: true, max: 100, ticks: {color: "#93a2bd"}, grid: {color: "#26334b"}}, y: {ticks: {color: "#c7d2e6"}, grid: {display: false}}}}
      });
    } catch (error) {
      console.error("Could not render expression chart:", error);
    }
  });
  if (window.reportCountData) {
    const el = document.getElementById("reportChart");
    if (el && Object.keys(window.reportCountData).length) new Chart(el, {
      type: "doughnut",
      data: {labels: Object.keys(window.reportCountData), datasets: [{data: Object.values(window.reportCountData), backgroundColor: ["#62e6dc","#9a8cff","#ffbd7b","#ff7f9e","#77a7ff","#b8e986","#d4a7ff"], borderColor: "#111a2d", borderWidth: 4}]},
      options: {responsive: true, plugins: {legend: {position: "bottom", labels: {color: "#c7d2e6", padding: 16}}}}
    });
  }
});
