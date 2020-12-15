
function submitForm(e) {
    let search_params = new URLSearchParams(window.location.search)
    let sort_opt = $('#sort').val();
    let search_text = $('#search_text').val();
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
    let search_params = new URLSearchParams(window.location.search)
    search_params.set('page', page_no);
    window.location.search = search_params.toString();
}

function resetSearch() {
    window.location.search = "page=1";
}

function selectFacet(param, value) {
    let search_params = new URLSearchParams(window.location.search)
    let selected_param_values = search_params.get(param);
    if (selected_param_values) {
        let selected = selected_param_values.split("|");
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
    window.location.search = search_params.toString();
}

document.onkeydown=function(e){
    if(e.which === 10 || e.which === 13) {
        submitForm();
    }
}
