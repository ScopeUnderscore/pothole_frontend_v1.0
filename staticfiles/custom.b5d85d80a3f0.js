$(document).ready(function () {
    // Ensure SweetAlert is loaded
    if (typeof Swal === "undefined") {
        alert("SweetAlert not loaded. Ensure you have included the CDN.");
    }

    // Initialize DOM elements
    const fileInput = $('#fileInput');
    const uploadArea = $('.upload-area');
    const browseBtn = $('.browse-files-btn');
    const analyzeBtn = $('.analyze-btn');
    const preview = $('.upload-preview');
    const resultMsg = $('.results-message');
    const spinner = $('#loading-spinner');
    const uploadText = $('.upload-text');
    const uploadIcon = $('.upload-icon');
    const uploadSubtext = $('.upload-subtext');
    let selectedFile = null;
    let resizedImageFile = null;

    browseBtn.click(function () {
        $("input[type='file']").click();
    });

    uploadArea.on('dragover', function (e) {
        e.preventDefault();
        $(this).addClass('dragover');
    });

    uploadArea.on('dragleave drop', function (e) {
        e.preventDefault();
        $(this).removeClass('dragover');
    });

    uploadArea.on('drop', function (e) {
        const file = e.originalEvent.dataTransfer.files[0];
        handleFile(file);
    });

    fileInput.on('change', function () {
        const file = this.files[0];
        handleFile(file);
    });

    function handleFile(file) {
        selectedFile = file;
        preview.empty();
        resultMsg.empty();
        resizedImageFile = null;

        if (!file) {
            resetUI();
            return;
        }

        const fileType = file.type;
        const fileName = file.name;

        if (!fileType.startsWith('image/') && !fileType.startsWith('video/')) {
            Swal.fire('Unsupported file type', 'Only images and videos are allowed.', 'warning');
            resetUI();
            selectedFile = null;
            return;
        }

        uploadText.text(`Selected: ${fileName}`);
        uploadIcon.hide();
        uploadSubtext.hide();

        analyzeBtn.text(fileType.startsWith('image/') ? "Analyze Image" : "Analyze Video");

        if (fileType.startsWith('image/')) {
            resizeImage(file);
        } else {
            const video = $('<video controls>')
                .attr('src', URL.createObjectURL(file))
                .addClass('uploaded-video')
                .css({ maxWidth: '100%', borderRadius: '8px' });
            preview.append(video);
        }
    }

    function resetUI() {
        uploadText.text("Drag and drop your file here");
        uploadIcon.show();
        uploadSubtext.show();
        analyzeBtn.text("Analyze");
        fileInput.val("");
    }

    function resizeImage(file) {
        const reader = new FileReader();

        reader.onload = function (event) {
            const img = new Image();
            img.src = event.target.result;

            img.onload = function () {
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');

                const maxSize = 640;
                let newWidth, newHeight;
                const aspectRatio = img.width / img.height;

                if (aspectRatio > 1) {
                    newWidth = maxSize;
                    newHeight = maxSize / aspectRatio;
                } else {
                    newHeight = maxSize;
                    newWidth = maxSize * aspectRatio;
                }

                canvas.width = maxSize;
                canvas.height = maxSize;

                const offsetX = (maxSize - newWidth) / 2;
                const offsetY = (maxSize - newHeight) / 2;

                ctx.fillStyle = "white";
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.drawImage(img, offsetX, offsetY, newWidth, newHeight);

                canvas.toBlob(function (blob) {
                    resizedImageFile = new File([blob], "resized_" + file.name, {
                        type: file.type,
                        lastModified: Date.now(),
                    });

                    const resizedPreview = $('<img>')
                        .attr('src', URL.createObjectURL(resizedImageFile))
                        .addClass('img-fluid uploaded-img')
                        .css({ maxWidth: '100%', borderRadius: '8px' });

                    preview.append(resizedPreview);
                }, file.type);
            };
        };

        reader.readAsDataURL(file);
    }

    analyzeBtn.on('click', function () {
        if (!selectedFile) {
            Swal.fire('No file selected', 'Please upload an image or video.', 'info');
            return;
        }

        const fileType = selectedFile.type;
        const formData = new FormData();

        if (fileType.startsWith('image/') && resizedImageFile) {
            formData.append('file', resizedImageFile);
        } else {
            formData.append('file', selectedFile);
        }

        spinner.show();
        resultMsg.empty();

        $.ajax({
            url: '/upload/',
            method: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function (response) {
                const { type, image_result, task_id } = response;

                if (type === 'image') {
                    spinner.hide();
                    displayImageResults(image_result);
                } else if (type === 'video') {
                    checkVideoStatus(task_id);
                }
            },
            error: function (xhr) {
                spinner.hide();
                Swal.fire('Upload Failed', xhr.responseText || 'An error occurred while uploading.', 'error');
            }
        });
    });

    function checkVideoStatus(taskId) {
        const interval = setInterval(() => {
            $.get(`/video-status/${taskId}`, function (response) {
                if (response.status === 'PENDING' || response.status === 'PROCESSING') return;

                clearInterval(interval);
                spinner.hide();

                if (response.status === 'SUCCESS') {
                    displayVideoResults(response.result);
                } else {
                    Swal.fire('Processing Failed', 'Something went wrong with the video processing.', 'error');
                }
            }).fail(() => {
                clearInterval(interval);
                spinner.hide();
                Swal.fire('Error', 'Failed to check task status.', 'error');
            });
        }, 3000);
    }

    function displayImageResults(data) {
        const { severity, pothole_percentage, image_url, potholes_detected } = data;

        const detectionText = potholes_detected > 0 ? `${potholes_detected} potholes detected.` : 'No potholes detected.';
        // const severityText = `Severity: ${severity.toFixed(2)}%`;
        const percentageText = `Pothole Area: ${pothole_percentage.toFixed(2)}%`;

        // <p><strong>${severityText}</strong></p>

        resultMsg.html(`
            <p><strong>${detectionText}</strong></p>
            <p><strong>${percentageText}</strong></p>
            <img src="${image_url}" class="img-fluid analyzed-img mt-2" alt="Analyzed Image">
        `);
    }

    function displayVideoResults(data) {
        const { average_severity, damaged_road_percentage, video_url, total_potholes_detected } = data;
        // <p><strong>Total Potholes:</strong> ${total_potholes_detected}</p>
        // <p><strong>Avg Severity:</strong> ${average_severity}%</p>
        resultMsg.html(`
            <p><strong>Damaged Road:</strong> ${damaged_road_percentage}%</p>
            <video controls class="analyzed-video" style="max-width:100%; border-radius: 8px;">
                <source src="${video_url}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
        `);
    }
});
