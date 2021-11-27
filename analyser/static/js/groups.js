$(document).ready(()=>{
    //alert("Ready")

});

$(document).on('click', '.assign_group_counselor', function () { 
    let group_id = $(this).data('group_id')
    $("#group_info_id").val(group_id)
    $('#assignCounselor').modal('show')
});


searchCounselor = () => {
    $("#counselors_div").empty()

    keyword = $("#search_keyword").val().trim();

    if (keyword.length < 3) {
        return;
    }

    ajax_data = { keyword: keyword, role: "business_counselor" };
    $.ajax({
        type: "POST", url: '/ajax_search_user_by_role', dataType: 'json', data: ajax_data,

        success: function (data) {
            if (!data.error) {
                populateCounselorsDiv(data)
            } else {
                console.log("error")
                console.log(data)
            }
        }
    });
}

populateCounselorsDiv = (all_personnel) => {
    let advisor_id = $("#select_advisor").val()
    ajax_data = { advisor_id: advisor_id };
    all_personnel.forEach(user => {
        // check whether current user
        row = '<li class="list-group-item d-flex justify-content-between">';
        row += user.first_name + ' ' + user.last_name;
        row += '<input type="hidden" value="' + user.pk_id + '">';
        row += '<button class="add_button btn btn-primary btn-sm"><i class="fa fa-plus"></i></button>'
        row += '</li>'

        $("#counselors_div").append(row)
    });
}

$(document).on('click', '.add_button', (e)=>{
    let list_element = e.target.parentElement;
    let counselor_id = list_element.children[0].value
    let group_id = $('#group_info_id').val()

    addCounselor(counselor_id, group_id);
    
});

addCounselor = (counselor_id, group_id) => {
    ajax_data = { counselor_id: counselor_id, group_id: group_id };
        $.ajax({
            type: "POST", url: '/ajax_assign_counselor_to_group', dataType: 'json', data: ajax_data,

            success: function (data) {
                console.log(data)
                if (!data.error) {
                    // $("#counselors_div").empty()
                    // counselorsAssignedToAdvisor()
                    $('#search_keyword').val("")
                    location.reload()
                } else {
                    console.log("error")
                    console.log(data)
                }
            }
        });
}
