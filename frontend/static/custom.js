$(document).ready(function () {
    // Ensure SweetAlert is working
    if (typeof Swal === "undefined") {
        alert("SweetAlert not loaded. Ensure you have included the CDN.");
    }

    // Trigger file input when "Browse Files" button is clicked
    $(".browse-files-btn").click(function () {
        $("input[type='file']").click();
    });

    // Handle file selection
    $("input[type='file']").change(function () {
        let file = this.files[0]; // Get selected file
        let fileName = file ? file.name : "";
        let fileType = file ? file.type : "";

        // Show the file name
        $(".upload-text").text(fileName ? `Selected: ${fileName}` : "Drag and drop your file here");

        // Hide upload icon and text when a file is selected
        $(".upload-icon, .upload-text, .upload-subtext").hide();

         // Show selected file name
        $(".upload-preview").html(`<p class="file-name"><strong>Selected:</strong> ${fileName}</p>`);


        // Validate file type
        if (!fileType.startsWith("image/") && !fileType.startsWith("video/")) {
            Swal.fire({
                icon: "error",
                title: "Invalid File Format",
                text: "Please upload an image or video file only.",
            });
            $(this).val(""); // Clear invalid file
            $(".upload-text").text("Drag and drop your file here");
            return;
        }
        // Update the Analyze button text based on the file type
        if (fileType.startsWith("image/")) {
            $(".analyze-btn").text("Analyse Image");
        } else if (fileType.startsWith("video/")) {
            $(".analyze-btn").text("Analyse Video");
        }


        // If file is an image, resize and display it
        if (fileType.startsWith("image/")) {
            let reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = function (event) {
                let img = new Image();
                img.src = event.target.result;
                img.onload = function () {
                    let canvas = document.createElement("canvas");
                    let ctx = canvas.getContext("2d");

                    // Set size while maintaining aspect ratio
                    canvas.width = 640;
                    canvas.height = 640;

                    let aspect = img.width / img.height;
                    let newWidth = aspect > 1 ? 640 : 640 * aspect;
                    let newHeight = aspect > 1 ? 640 / aspect : 640;

                    let offsetX = (640 - newWidth) / 2;
                    let offsetY = (640 - newHeight) / 2;
                    ctx.drawImage(img, offsetX, offsetY, newWidth, newHeight);

                    canvas.toBlob(function (blob) {
                        let resizedFile = new File([blob], "resized_" + file.name, {
                            type: file.type,
                            lastModified: Date.now(),
                        });

                        // Create a URL for the resized image
                        let imageURL = URL.createObjectURL(resizedFile);

                        // Update the preview section with the resized image
                        $(".upload-preview").html(`
                            <img src="${imageURL}" class="uploaded-img img-fluid" alt="Resized Image">
                        `);

                        // Add resized file to FormData
                        formData.set("file", resizedFile);
                    }, file.type);
                };
            };
        }

        // If file is a video, display it in the upload section
        else if (fileType.startsWith("video/")) {
            let videoURL = URL.createObjectURL(file);
            $(".upload-preview").html(`
                <video width="400" controls>
                    <source src="${videoURL}" type="${fileType}">
                    Your browser does not support the video tag.
                </video>
            `);
        }
    });

    // Handle analyze button click
    $(".analyze-btn").click(function (event) {
        event.preventDefault();

        let fileInput = $("input[type='file']")[0].files[0];
        if (!fileInput) {
            Swal.fire({
                icon: "warning",
                title: "No File Selected",
                text: "Please select an image or video before analyzing.",
            });
            return;
        }

        let fileType = fileInput.type;
        let formData = new FormData();
        formData.append("file", fileInput);

        $("#loading-spinner").show();
        $(".results-message").html("");

        // If the file is an image, resize it before sending to backend
        if (fileType.startsWith("image/")) {
            let reader = new FileReader();
            reader.readAsDataURL(fileInput);
            reader.onload = function (event) {
                let img = new Image();
                img.src = event.target.result;
                img.onload = function () {
                    let canvas = document.createElement("canvas");
                    let ctx = canvas.getContext("2d");

                    // Set size while maintaining aspect ratio
                    canvas.width = 640;
                    canvas.height = 640;

                    let aspect = img.width / img.height;
                    let newWidth = aspect > 1 ? 640 : 640 * aspect;
                    let newHeight = aspect > 1 ? 640 / aspect : 640;

                    let offsetX = (640 - newWidth) / 2;
                    let offsetY = (640 - newHeight) / 2;
                    ctx.drawImage(img, offsetX, offsetY, newWidth, newHeight);

                    canvas.toBlob(function (blob) {
                        let resizedFile = new File([blob], "resized_" + fileInput.name, {
                            type: fileInput.type,
                            lastModified: Date.now(),
                        });

                        formData.set("file", resizedFile);
                        sendFileToBackend(formData, fileType);
                    }, fileInput.type);
                };
            };
        } else if (fileType.startsWith("video/")) {
            sendFileToBackend(formData, fileType);
        }
    });

    // Function to send file data to backend via AJAX
    function sendFileToBackend(formData, fileType) {
        $.ajax({
            url: "/api/detect/",
            type: "POST",
            data: formData,
            contentType: false,
            processData: false,
            success: function (response) {
                $("#loading-spinner").hide();
                

                Swal.fire({
                    icon: "success",
                    title: "Analysis Complete",
                    text: "File processed successfully!",
                });

                // Display analyzed results
                if (fileType.startsWith("image/")) {
                    let mediaUrl = response.image_url;
                    $(".results-message").html(`
                        <h4>Detection Results:</h4>
                        <p><strong>Severity:</strong> ${response.severity}%</p>
                        <p><strong>Objects Detected:</strong> ${response.objects}</p>
                        <img src="${mediaUrl}" class="analyzed-img img-fluid mt-2" alt="Analyzed Image">
                    `);
                } else if (fileType.startsWith("video/")) {
                    let videoUrl = response.video_url;
                    $(".results-message").html(`
                        <h4>Detection Results:</h4>
                        <p><strong>Severity:</strong> ${response.severity}%</p>
                        <p><strong>Objects Detected:</strong> ${response.objects}</p>
                        <video width="400" controls>
                            <source src="${videoUrl}" type="video/mp4">
                            Your browser does not support the video tag.
                        </video>
                    `);
                }
            },
            error: function (xhr, status, error) {
                $("#loading-spinner").hide();

                // Handle API errors properly
                let errorMessage = xhr.responseJSON?.error || "An unknown error occurred.";

                Swal.fire({
                    icon: "error",
                    title: "Upload Failed",
                    text: errorMessage,
                });
            },
        });
    }

        // // Function to show popup when an image is clicked
        // function showPopup(imageUrl) {
        //     let popup = document.getElementById("imagePopup");
        //     let popupImage = document.getElementById("popupImage");

        //     popupImage.src = imageUrl;
        //     popup.style.display = "flex"; // Show the popup
        // }

        // // Function to close the popup when clicking "X"
        // document.querySelector(".close-popup").addEventListener("click", function() {
        //     document.getElementById("imagePopup").style.display = "none";
        // });

        // // Close popup when clicking outside the image
        // document.getElementById("imagePopup").addEventListener("click", function(event) {
        //     if (event.target === this) {
        //         this.style.display = "none";
        //     }
        // });

        // // Attach click event to uploaded and analyzed images dynamically
        // document.addEventListener("click", function(event) {
        //     if (event.target.classList.contains("uploaded-img") || event.target.classList.contains("analyzed-img")) {
        //         showPopup(event.target.src);
        //     }
        // });

    
});
