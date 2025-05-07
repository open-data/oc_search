
function submitForm(e) {
    search_params = new URLSearchParams(window.location.search);
    sort_opt = $('#sort').val();
    search_text = $('#search_text').val();
    search_params.set('sort', sort_opt);
    search_params.set('search_text', search_text)
    search_params.set('page', '1');
    console.log(search_params.toString());
    window.location.search = search_params.toString();
}

function submitFormOnEnter(e) {
    if(e.which === 10 || e.which === 13) {
        submitForm();
    }
}

function gotoPage(page_no) {
    search_params = new URLSearchParams(window.location.search)
    search_params.set('page', page_no);
    window.location.search = search_params.toString();
}

function selectFacet(param, value) {
    search_params = new URLSearchParams(window.location.search)
    selected_param_values = search_params.get(param);
    if (selected_param_values) {
        selected = selected_param_values.split("|");
        // If the value is already a search parameter, then remove it.
        if (selected.indexOf(value) > -1) {
            selected = selected.filter( function (e) {
                return e !== value;
            });
        // Otherwise add the new search value
        } else {
            selected.push(value);
        }
        if (selected.length === 0) {
            search_params.delete(param);
        } else {
            search_params.set(param, selected.join("|"));
        }
    } else {
        // Add new search facet
        search_params.set(param, value);
    }
    search_params.set('page', '1');
    search_params.set('sort', $('#sort').val());
    window.location.search = search_params.toString();
}

document.onkeydown=function(e){
    if(e.which === 10 || e.which === 13) {
        submitForm();
    }
}

function export_results(url){
    let xhr = new XMLHttpRequest();
    xhr.open("POST", url, true);

    //Send the proper header information along with the request
    xhr.setRequestHeader("Content-type", "application/x-www-form-urlencoded");

    xhr.send(params);

    // CUTE, but this doesn<t take you to the download page, try as a form
}
