/**
 * The google picker functionality
 */
let tokenClient;
let accessToken = null;
let pickerInited = false;
let gisInited = false;

const GOOGLE_API_KEY = "AIzaSyBViUoUiqmE_aI1pQMkhZHlnUIlSvMl7c8";

// Use the API Loader script to load google.picker
function onApiLoad() {
  console.log("onApiLoad");
  gapi.load("picker", onPickerApiLoad);
}

function onPickerApiLoad() {
  console.log("onPickerApiLoad");
  pickerInited = true;
}

function gisLoaded() {
  console.log("gisLoaded");
  // TODO(developer): Replace with your client ID and required scopes.
  tokenClient = google.accounts.oauth2.initTokenClient({
    client_id:
      "336201100300-c8ate94r10ihhquhh8v33o1gre2nijbo.apps.googleusercontent.com",
    scope: "https://www.googleapis.com/auth/drive.file",
    callback: "", // defined later
  });
  gisInited = true;
  console.log("tokenClient ", tokenClient);
}

// Create and render a Google Picker object for selecting from Drive.
function createPicker() {
  console.log("Clicked picker");
  const showPicker = () => {
    // TODO(developer): Replace with your API key
    const picker = new google.picker.PickerBuilder()
      .addView(google.picker.ViewId.DOCS)
      .setOAuthToken(accessToken)
      .setDeveloperKey(GOOGLE_API_KEY)
      .setCallback(pickerCallback)
      .build();
    picker.setVisible(true);
  };

  // Request an access token.
  tokenClient.callback = async (response) => {
    if (response.error !== undefined) {
      throw response;
    }
    accessToken = response.access_token;
    console.log("Access Token ", accessToken);
    showPicker();
  };

  if (accessToken === null) {
    // Prompt the user to select a Google Account and ask for consent to share their data
    // when establishing a new session.
    tokenClient.requestAccessToken({ prompt: "consent" });
  } else {
    // Skip display of account chooser and consent dialog for an existing session.
    tokenClient.requestAccessToken({ prompt: "" });
  }
}
/**
 * Called after the action took place
 * @param {*} data
 */
function pickerCallback(data) {
  if (data[google.picker.Response.ACTION] == google.picker.Action.PICKED) {
    let doc = data[google.picker.Response.DOCUMENTS][0];
    console.log("Selected ", doc);
    const fileId = doc.id;
    const fileName = doc.name;
    // Download file and send it to backend
    download_file(fileId);
  }
}

/**
 * Download file from google drive
 * @param {*} fileId
 */
function download_file(fileId) {
  var url = `https://www.googleapis.com/drive/v3/files/${fileId}?alt=media&mimeType=text/plain&key=${GOOGLE_API_KEY}`;
  console.log(url);
  $.ajax({
    url: url,
    method: "GET",
    xhrFields: {
      responseType: "blob",
    },
    success: function (data) {
      console.log("Got file data from google ", data);
      // send the file to backend
      sendFileId(data);
    },
    error: function (xhr, status, error) {
      console.error("Downloading the file failed", error);
    },
  });
}

/**
 * Sends the file Id to the backend where the processing happens
 * @param {*} blob
 */
function sendFileId(blob) {
  var formData = new FormData();
  formData.append("file", blob);
  $.ajax({
    type: "POST",
    url: window.location.origin + "/upload_file",
    data: formData,
    contentType: false,
    processData: false,
    success: function (response) {
      $.notify(
        { message: "Successfully processed, check your email inbox." },
        { type: "success" }
      );
    },
    error: function (xhr, status, error) {
      $.notify(
        { message: "Couldn't process the uploaded file, " + error.message },
        { type: "danger" }
      );
    },
  });
}

/**
 *
 * Local file upload handlers
 */
function appendInvisibleInput() {
  /**Listen to the invisible file uploader */
  $("#local-file-picker").off();
  $("#local-file-picker").on("input", function () {
    let selectedFile = $(this).prop("files")[0];
    if (selectedFile && selectedFile.name.endsWith(".txt")) {
      console.log("Selected .txt file:", selectedFile);
      sendFileId(selectedFile);
      // Handle the selected file here
    } else {
      console.log("Please select a valid .txt file.");
    }
  });
  $("#local-file-picker").click();
}

function appendInvisibleFileInput() {
  let fileInput = $(
    '<input type="file" id="local-file-picker" style="display: none;">'
  );
  $("body").append(fileInput);
}

/**
 * Listen to button click and attach createPicker
 */
appendInvisibleFileInput();
let driverPicker = document.getElementById("open-drive-picker");
if (driverPicker) {
  driverPicker.addEventListener("click", createPicker);
}

let localPicker = document.getElementById("open-local-picker");
if (localPicker) {
  localPicker.addEventListener("click", appendInvisibleInput);
}
