$(document).ready(function () {
    const url = $('#task_id').val();
    let task_url = $('#download_status_url').val();

    $.get(task_url)
        .done(function pollAsyncResults(data) {
            context: this
            $.get(task_url)
                .done(function (asyncData, status, xhr)
            {
                context: this
                let msg_elem = $('#waiting_msg');
                let delay_msg = $('#delay_msg')
                if ((xhr.status === 200) && (asyncData.task_status === 'SUCCESS')) {
                    msg_elem.empty();
                    delay_msg.empty();
                    let success_msg = document.createElement("p");
                    success_msg.innerText = asyncData.message;
                    msg_elem.append(success_msg);
                    let icon_elem = document.createElement("span");
                    icon_elem.setAttribute("class", "glyphicon glyphicon-download-alt");
                    icon_elem.setAttribute("aria-hidden", "true");
                    let file_link = document.createElement("a");
                    file_link.id = "download-btn";
                    file_link.setAttribute("class", "btn btn-success active")
                    file_link.setAttribute("role", "button");
                    file_link.innerHTML = icon_elem.outerHTML + " " + asyncData.button_label;
                    file_link.href = asyncData.file_url;
                    msg_elem.append(file_link);
                    if ($("#task_started").length) {
                        $("#task_started").html(asyncData.start);
                    }
                    if ($("#task_done").length) {
                        $("#task_done").html(asyncData.done);
                    }
                } else if ((xhr.status === 202) || (xhr.status === 200 && asyncData.task_status !== 'SUCCESS')) {
                    clearTimeout(pollAsyncResults);
                    let waiting_msg = document.createElement("p");
                    let icon_elem = document.createElement("i");
                    icon_elem.setAttribute("class", "fa fa-refresh fa-spin fa-2Yx fa-fw");
                    icon_elem.setAttribute("aria-hidden", "true");
                    waiting_msg.innerHTML = asyncData.message + " " + icon_elem.outerHTML;
                    msg_elem.empty();
                    msg_elem.append(waiting_msg);
                    setTimeout(function () {
                        pollAsyncResults(pollAsyncResults)
                    }, 1000);
                } else {
                    waiting_msg.innerText = asyncData.message;
                    msg_elem.empty();
                    msg_elem.append(waiting_msg);
                }
            })
        })
    })
