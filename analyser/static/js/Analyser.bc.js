function Analyser(){
    this.checkbox_template = "<input type='checkbox' class='selector' id='%s' />";
    this.edit_template = "<button class='%s btn btn-outline-info btn-sm' data-toggle='modal' data-target='%s' data-object_type='%s' data-row-id='%s' data-action='edit'>Edit</button>";
    this.delete_template = "<button class='%s btn btn-outline-danger btn-sm' data-object_type='%s' data-action='delete' data-row-id='%s' data-toggle='modal' data-target='#confirmModal' >Delete</button>";
    this.activate_template = "<button class='%s btn btn-outline-%s btn-sm' data-object_type='%s' data-row-id='%s' data-toggle='modal' data-action='%s' data-target='#confirmModal'>%s</button>";

    // add the csrf token before ajax requests
    this.csrftoken = $('meta[name=csrf-token]').attr('content');
    $.ajaxSetup({
      beforeSend: function(xhr, settings) {
        if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type)) {
            xhr.setRequestHeader("X-CSRFToken", analyser.csrftoken)
        }
      }
    });

    this.graph_credits = { text: 'TNS Chat Analyser', href: '#' };
    
    this.button_settings = {
        'user': {
            'is_long_process': false,
            'url': '_user/',
            'table': undefined,
            'form': 'add_user',
            'success_message': 'The user has been modified successfully'
        }
    }
};

Analyser.prototype.initiatePages = function(){
    if(window.location.pathname == '/dashboard.bc') this.initiateDashboard();
    else if(window.location.pathname == '/whatsapp_groups_bc') this.initiateGroups();
    else if(window.location.pathname == '/engaged_users') this.initiateEngagedUsers();
    else if(window.location.pathname.split('/')[1] == 'group_stats') this.initiateGroupStats();
    else if(window.location.pathname.split('/')[1] == 'user_stats') this.initiateUserStats();
    else if(window.location.pathname == '/files_repo') this.initiateFilesRepo();
    else if(window.location.pathname == '/users') analyser.initiateSysUsers();
};

Analyser.prototype.initiateSysUsers = function(event){
    analyser.button_settings['user']['table'] = $('#sys_users').DataTable({
        "ajax": {
            url: 'data/users',
            type:'GET',
            "dataSrc": function ( json ) {
                analyser.cur_attendance_dates = json['dates'];
                return json['data'];
            }
        },
        "deferRender": true,
        "columnDefs": [
            {
                "data": "selector",
                "targets": 0, 
                render: function ( data, type, row, meta ) {
                    return sprintf(analyser.checkbox_template, row.pk_id);
                }
            },
            {"data": "first_name", "targets": 1 },
            {"data": "last_name", "targets": 2 },
            {"data": "username", "targets": 3 },
            {"data": "email", "targets": 4 },
            {"data": "tel", "targets": 5 },
            {"data": "designation", "targets": 6 },
            {
                "data": "is_active",
                "targets": 7, 
                render: function ( data, type, row, meta ) {
                    return row.is_active ? 'Yes' : 'No';
                }
            },
            {
                "data": "actions",
                "targets": 8, 
                render: function ( data, type, row, meta ) {
                    edit_btn = sprintf(analyser.edit_template, 'edit_user', '#newUser', 'user', row.pk_id);
                    delete_btn = sprintf(analyser.delete_template, 'delete_user', 'user', row.pk_id);

                    activate_btn = sprintf(analyser.activate_template,
                        row.is_active ? 'deactivate_user' : 'activate_user',
                        row.is_active ? 'secondary' : 'success',
                        'user',
                        row.pk_id,
                        row.is_active ? 'deactivate' : 'activate',
                        row.is_active ? 'Deactivate' : 'Activate'
                    )

                    return edit_btn + activate_btn + delete_btn;
                }
            }
        ]
    });
    $('div.dataTables_filter input').addClass('form-control-clean')
    MicroModal.init();
    analyser.initiateActionButtons('newUser');

    // bind confirm_save button
    $('#confirm_save').on('click', function(){
        // 1. validate the entered data
        var new_user = $("[name=add_user]");
        analyser.newuser_validator = new_user.validate({
            debug: true,

            rules: {
                email: {
                    email: true,
                    remote: {
                        url: "validate_input",
                        async: false                // find a way to remove this
                    }
                },
                first_name: {minlength: 3},
                surname: {minlength: 3},
                username: {
                    minlength: 3,
                    remote: {
                        url: "validate_input",
                        async: false                // find a way to remove this
                    }
                },
                tel: {
                    regex: '^(\\+254|0)(1|7)[0-9]{8}$',
                    remote: {
                        url: "validate_input",
                        async: false                // find a way to remove this
                    }
                },
            },
            messages: {
                tel: { remote: "This telephone is already in use" },
                email: { remote: "This email is already in use"},
                username: { remote: "This username is already in use"}
            }
        });
        isValid = false;
        isValid = new_user.valid();
        if( isValid ){
            analyser.cur_action = 'add';
            analyser.cur_object = 'user';
            analyser.ajax_data = objectifyForm($('[name=add_user]').serializeArray());
            analyser.cur_modal = 'newUser';
            $('#confirmModal').modal();
            analyser.refresh_table = analyser.users_table;
        }
        else{
            analyser.first_modal = undefined;
        }
        // 2. Call the action to confirm the save user action and pass the data
    });

    analyser.initiateObjectManagement();
};

Analyser.prototype.initiateObjectManagement = function(){
    $('#confirmModal').on('show.bs.modal', function (event) {
        var button = event.relatedTarget;
        if(button != undefined){
            analyser.cur_object = $(button).data('object_type');
            analyser.cur_action = $(button).data('action');
            $('#confirm').data('object_id', $(button).data('row-id'));
            analyser.ajax_data = {'object_id': $(button).data('row-id')};
        }

        // change the modal message
        $('#modal_title').html('Confirm '+ analyser.cur_action +'!');
        var modal_message = 'Are you sure you want to <strong>'+ analyser.cur_action +'</strong> this <strong>'+ analyser.cur_object +'</strong>. ';
        if(analyser.cur_action == 'delete'){
            modal_message += 'This action is not reversible.';
        }

        if(analyser.button_settings[analyser.cur_object]['is_long_process']){
            modal_message += "<br /><br />This will take a few seconds as we save the changes and update the data collection app...";
        }

        $('#modal_message').html(modal_message);
        $('#confirm').html(analyser.cur_action);
    });

    $('#confirm').on('click', function () {
        if(analyser.cur_object == 'elisa_results'){
            $('#'+analyser.button_settings[analyser.cur_object]['form']).submit();
            return true;
        }

        // formulate the url
        var url = '/' + analyser.cur_action + analyser.button_settings[analyser.cur_object]['url'];
        analyser.refresh_table = analyser.button_settings[analyser.cur_object]['table'];
        analyser.showProcessing();
        $.ajax({
            type: "POST", url: url, dataType: 'json', data: analyser.ajax_data,
            error: analyser.communicationError,
            success: function (data) {
                analyser.endShowProcessing();
                if (data.error) {
                    $.notify({message: data.message}, {type: 'danger'});
                    $('#confirmModal').modal('hide');
                    return;
                } else {
                    var message = data.message == undefined ? analyser.button_settings[analyser.cur_object]['success_message'] : data.message;
                    $.notify({message: message}, {type: 'success'});
                    $('#confirmModal').modal('hide');
                    $('.modal-backdrop').remove();
                    $('.modal-backdrop').remove();
                    $('#'+analyser.cur_modal).modal('hide');
                    // we might need to update the pre-requisite table
                    analyser.button_settings[analyser.cur_object]['table'].ajax.reload();
                    $('[name='+ analyser.button_settings[analyser.cur_object]['form'] +']').trigger("reset");
                    analyser.cur_action = undefined;
                }
            }
        });
    });
};

Analyser.prototype.initiateActionButtons = function(id_){
    $('#'+id_).on('show.bs.modal', function (event) {
        var button = event.relatedTarget;
        analyser.cur_object = $(button).data('object_type');
        analyser.cur_action = $(button).data('action');
        if(analyser.newuser_validator != undefined){
            analyser.newuser_validator.resetForm();
            $('.form-control.error').removeClass('error');
            // analyser.newuser_validator.destroy();
        }
    });
};

Analyser.prototype.initiateGroups = function () {
    analyser.initiateSearchAutocomplete();
    analyser.initiateDateRanges();
    var table = $('#whatsapp_groups').DataTable({
        "processing": true,
        // "serverSide": true,
        "data": analyser.page_data,
        "rowId": 'group_id',
        "columns": [
            {
                "data": "selector",
                "orderable": false,
                "targets": 0,
                render: function (data, type, row, meta) {
                    return sprintf(analyser.checkbox_template, row.group_id);
                }
            },
            {
                "data": "group_name",
                "targets": 1,
                render: function (data, type, row, meta) {
                    return "<a href='#' class='group_link' data-group_id='" + row.group_id + "'>" + row.group_name + "</a>";
                }
            },
            { "data": "date_created", "targets": 2 },
            { "data": "created_by", "targets": 3 },
            { "data": "new_users_", "targets": 4 },
            { "data": "left_users_", "targets": 5 },
            { "data": "no_messages_", "targets": 6 },
            // { "data": "no_images_", "targets": 7 },
            // { "data": "no_links_", "targets": 8 },
            { "data": "counselor_", "targets": 9 },
            // {
            //     "data": "settings_",
            //     "targets": 10,
            //     render: function (data, type, row, meta) {
            //         return "<a href='#' class='assign_group_counselor' data-group_id='" + row.group_id + "'>" + "Assign Counselor" + "</a>";
            //     }
            // },
        ]
    });
    table.columns().iterator('column', function (ctx, idx) {
        $(table.column(idx).header()).append('<span class="sort-icon"/>');
    });

    $('div.dataTables_filter input').addClass('form-control-clean');
    MicroModal.init();

    $(document).on('click', '.group_link', function () { analyser.showItemStats(sprintf('/group_stats/%s', $(this).data('group_id'))); });
};

Analyser.prototype.initiateEngagedUsers = function(){
    analyser.initiateSearchAutocomplete();
    analyser.initiateDateRanges();
    var table = $('#engaged_users').DataTable({
        "processing": true,
        "serverSide": true,
        "ajax": $.fn.dataTable.pipeline( {
            url: 'data/engaged_users',
            pages: 5,                       // number of pages to cache
            type:'POST'
        } ),
        "rowId": 'pk_id',
        "deferRender": true,
        // dom: 'Bfrtip',
        "columnDefs": [
            {
                "data": "selector",
                "orderable": false,
                "targets": 0, 
                render: function ( data, type, row, meta ) {
                    return sprintf(analyser.checkbox_template, row.pk_id);
                }
            },
            {
                "data": "name_phone",
                "targets": 1,
                render: function ( data, type, row, meta ) {
                    return "<a href='#' class='user_link' data-group_id='"+ row.group_id +"' data-user_id='"+ row.name_phone +"'>"+ row.name_phone +"</a>";
                }
            },
            {
                "data": "group_name",
                "targets": 2,
                render: function ( data, type, row, meta ) {
                    return "<a href='#' class='group_link' data-group_id='"+ row.group_id +"'>"+ row.group_name +"</a>";
                }
            },
            {"data": "no_messages", "targets": 3 },
            {"data": "no_images", "targets": 4 },
            {"data": "no_links", "targets": 5 }
        ]
    });

    table.columns().iterator( 'column', function (ctx, idx) {
        $( table.column(idx).header() ).append('<span class="sort-icon"/>');
    } );

    $(document).on('click', '.user_link', function(){ analyser.showItemStats(sprintf('/user_stats/%s/%s', $(this).data('group_id'), $(this).data('user_id'))); });
    $(document).on('click', '.group_link', function(){ analyser.showItemStats(sprintf('/group_stats/%s', $(this).data('group_id'))); });
};

Analyser.prototype.initiateFilesRepo = function(){
    analyser.files_table = $('#exported_chats').DataTable({
        "processing": true,
        "language": {
            processing: '<i class="fa fa-spinner fa-spin fa-3x fa-fw"></i><span class="sr-only">Loading..n.</span> ',
        },
        "serverSide": true,
        "ajax": $.fn.dataTable.pipeline( {
            url: 'data/exported_files',
            pages: 5,                       // number of pages to cache
            type:'POST'
        } ),
        "rowId": 'id',
        "deferRender": true,
        "columnDefs": [
            {
                "data": "selector",
                "targets": 0, 
                render: function ( data, type, row, meta ) {
                    return sprintf(analyser.checkbox_template, row.pk_id);
                }
            },
            {"data": "title", "targets": 1 },
            {"data": "group_name", "targets": 2 },
            {"data": "datetime_created", "targets": 3 },
            {"data": "filesize", "targets": 4 },
            {"data": "status", "targets": 5 },
            {"data": "email", "targets": 6, "sWidth": "25%" },
            {
                "data": "actions",
                "targets": 7, 
                render: function ( data, type, row, meta ) {
                    edit_btn = sprintf(analyser.edit_template, 'reprocess_file', '#reprocessFile', 'reprocess_file', row.pk_id);
                    return edit_btn;
                }
            }
            
        ]
    });

    $('div.dataTables_filter input').addClass('form-control-clean');
    MicroModal.init();

    $('#confirm_file_process').on('click', function () {
        analyser.showProcessing();
        $.ajax({
            type: "POST", url: '/process_new_chats', dataType: 'json',
            error: analyser.communicationError,
            success: function (data) {
                analyser.endShowProcessing();
                if (data.error) {
                    $.notify({message: data.message}, {type: 'danger'});
                    $('#process_files').modal('hide');
                    return;
                } else {
                    var message = data.message == undefined ? analyser.button_settings[analyser.cur_object]['success_message'] : data.message;
                    $.notify({message: message}, {type: 'success'});
                    $('#process_files').modal('hide');
                    $('.modal-backdrop').remove();
                    $('.modal-backdrop').remove();
                    $('#'+analyser.cur_modal).modal('hide');
                    // we might need to update the pre-requisite table
                    analyser.files_table.ajax.reload();
                }
            }
        });
    });
};

Analyser.prototype.showProcessing = function(){
    $('#overlay, .cssload-loader').css('display', 'flex');
};

Analyser.prototype.endShowProcessing = function(){
    $('#overlay, .cssload-loader').css('display', 'none');
};

Analyser.prototype.initiateDashboard = function(){
    analyser.initiateSearchAutocomplete();
    analyser.initiateDateRanges();

    var gauge1 = Gauge(
      document.getElementById("processing_progress"), {
        max: 100,
        dialStartAngle: -90,
        dialEndAngle: -90.001,
        value: 100,
        label: function(value) {
          return (Math.round(value * 100) / 100) + '%';
        }
      }
    );
    gauge1.setValueAnimated(analyser.stats.perc_processed, 1);
};

Analyser.prototype.initiateGroupStats = function(){
    analyser.initiateSearchAutocomplete();
    analyser.initiateDateRanges();
    analyser.drawGroupStatsGraphs();
};

Analyser.prototype.initiateDateRanges = function(){
    if(analyser.stats == undefined || analyser.stats.max_date == undefined){
        my_max_date = moment().format('DD/MM/YYYY');
        my_min_date = moment().subtract(730, 'days').format('DD/MM/YYYY');
    }
    else{
        my_max_date = moment(analyser.stats.max_date, 'DD/MM/YYYY').format('DD/MM/YYYY');
        my_min_date = moment(analyser.stats.min_date, 'DD/MM/YYYY').format('DD/MM/YYYY');
    }

    picker_settings = {
        "locale": {
            "format": "DD/MM/YYYY"
        },
        'maxDate': my_max_date,
        'minDate': my_min_date
    }
    
    if(analyser.stats == undefined || analyser.stats.s_date == undefined){
        picker_settings['startDate'] = moment().subtract(90, 'days').format('DD/MM/YYYY');
        picker_settings['endDate'] = moment().subtract(60, 'days').format('DD/MM/YYYY');
    }
    else{
        picker_settings['startDate'] = moment(analyser.stats.s_date, 'DD/MM/YYYY').format('DD/MM/YYYY');
        picker_settings['endDate'] = moment(analyser.stats.e_date, 'DD/MM/YYYY').format('DD/MM/YYYY');
    }

    $('input[name="analysis_range"]').daterangepicker(picker_settings);
    $('input[name="analysis_range"]').on('apply.daterangepicker', function(ev, picker){ analyser.showItemStats(window.location.pathname); });
};

Analyser.prototype.drawGroupStatsGraphs = function () {
    Highcharts.chart('categories_chart', {
        colors :['#00b0af','#d1e97b','#f4e61e','#470f61'],
        chart: {
            plotBackgroundColor: null,
            plotBorderWidth: null,
            plotShadow: false,
            type: 'pie'
        },
        title: { text: '' },
        credits: analyser.graph_credits,
        tooltip: {
            headerFormat: '',
            pointFormat: '<span style="color:{point.color}">\u25CF</span> <b> {point.name}</b><br/>' +
                'Count: <b>{point.y}</b><br/>'
        },
        plotOptions: {
            pie: {
                allowPointSelect: true,
                cursor: 'pointer',
                size: '80%',
                center: ['50%', '50%'],
                showInLegend: true,
                dataLabels: {
                    enabled: true,
                    distance: -50,
                    formatter: function () { return sprintf('%s: %.1f%%', this.point.name, (this.point.y / analyser.stats.totals) * 100); }
                }
            }
        },
        series: [{

            // minPointSize: 10,
            // maxPointSize: 200,
            innerSize: '20%',
            // colorByPoint: true,
            credits: { enabled: false },
            // zMin: 0,
            name: 'information',
            data: [

                { name: 'Messages', y: analyser.stats.messages_count },
                { name: 'Images', y: analyser.stats.images_count },
                { name: 'Links', y: analyser.stats.links_count },
                { name: 'Emojis', y: analyser.stats.emojis_count }
            ]
        }]
    });

    Highcharts.chart('active_days', {
        chart: { zoomType: 'xy' },
        title: { text: '' },
        xAxis: {
            categories: (analyser.stats.active_dates && analyser.stats.active_dates.dates) || '' ,
            crosshair: true
        },
        credits: analyser.graph_credits,
        yAxis: [{
            min: 0,
            title: { text: 'No of messages' }
        }, {
            min: 0,
            title: { text: 'Active users' },
            opposite: true
        }],
        tooltip: {
            headerFormat: '<span style="font-size:10px">{point.key}</span><table>',
            pointFormat: '<tr><td style="color:{series.color};padding:0">{series.name}: </td>' +
                '<td style="padding:0"><b>{point.y}</b></td></tr>',
            footerFormat: '</table>',
            shared: true,
            useHTML: true
        },
        plotOptions: {
            column: {
                pointPadding: 0.2,
                borderWidth: 0
            },
            series: {
                point: {
                    events: {
                        click() {
                            let point = this;

                            let date = point.category;
                            let sent_messages = point.y;
                            let group_id = $("#group_id").val()
                           
                            ajax_data = { 'group_id': $("#group_id").val(), date: point.category };
                           
                            $("#date_selected").html(date)
                          
                            $.ajax({
                                type: "POST", url: '/searchGroupChatByDate', dataType: 'json', data: ajax_data,
                                
                                success: function (data) {
                                    console.log(data)
                                    populateChatDiv(data)
                                    
                                }
                            });

                            $("#exampleGetChatHistory").modal('show')
                            //console.log(sent_messages)
                        }
                    }
                }
            }
        },
        series: [{
            name: 'Sent Messages',
            type: 'column',
            color:'#d1e97b',
            data: (analyser.stats.active_dates && analyser.stats.active_dates.messages) || []

        }, {
            name: 'Active Users',
            yAxis: 1,
            type: 'spline',
            color:'#00b0af',
            data: (analyser.stats.active_dates && analyser.stats.active_dates.users) || []

        }]
    });

    console.log(analyser.emotions)
    stopwords = ['and','i','me','my','myself','we','our','ours','ourselves','you','your','yours','yourself','yourselves','he','him','his','himself','she','her','hers','herself','it','its','itself','they','them','their','theirs','themselves','what','which','who','whom','this','that','these','those','am','is','are','was','were','be','been','being','have','has','had','having','do','does','did','doing','a','an','the','and','but','if','or','because','as','until','while','of','at','by','for','with','about','against','between','into','through','during','before','after','above','below','to','from','up','down','in','out','on','off','over','under','again','further','then','once','here','there','when','where','why','how','all','any','both','each','few','more','most','other','some','such','no','nor','not','only','own','same','so','than','too','very','s','t','can','will','just','don','should','now','na',
                'kwa',"'t","mimi", "yangu", "mwenyewe", "sisi", "yetu", "wenyewe",
         "wewe", "yako", "yeye", "wake", "ni", "yake", "yenyewe", "wao" ,
          "nini", "yupi", "nani", "huyu", "huyo", "hawa", "wale", "wapo",
           "ilikuwa", "walikuwa", "kuwa", "amekuwa", "alikuwa", "na", "kufanya" ,
            "anafanya", "alifanya", "alifanya", "hiyo", "lakini", "ikiwa", "au",
             "kwa sababu", "kama", " mpaka", "wakati", "ya", "kwa", "pamoja na",
              "karibu", "dhidi ya", "kati", 
             "ndani", "kupitia", "kabla", "baada ya", "juu", "chini", "hadi", "kutoka", "nje",
              "washa", "zima", "tena", "zaidi", "basi", "mara moja", "hapa", "hapo", "wakati",
               "wapi", "kwa nini", "vipi", "wote" , "yoyote", "kila", "wachache",
                "zaidi", "wengi", "nyingine",
                "baadhi", "kama", "hapana", "wala",
              "sio", "tu ", "miliki", "sawa", "hivyo", "kuliko", "pia", "sana", "naweza",
               "unaweza", "anaweza", "tu", "lazima", "sasa "]


    
    let words = $("#tokenized_text").html()
    // const text = words
    // console.log(text)
    const text = words,
        lines = text.split(/[,\. ]+/g),
        data = lines.reduce((arr, word) => {
            let obj = Highcharts.find(arr, obj => obj.name === word);

            if (obj) {
                obj.weight += 1;
            } else {
                obj = {
                    name: word,
                    weight: 1
                };
            arr.push(obj);
            }
            return arr;
        }, []);


    Highcharts.chart('word_cloud', {
        accessibility: {
            screenReaderSection: {
                beforeChartFormat: '<h5>{chartTitle}</h5>' +
                    '<div>{chartSubtitle}</div>' +
                    '<div>{chartLongdesc}</div>' +
                    '<div>{viewTableButton}</div>'
            }
        },
        series: [{
            type: 'wordcloud',
            data,
            name: 'Occurrences',
           colors :['#f4e61e','#00b0af','#d1e97b','#470f61'],
            
        }],
        title: {
            text: ''
        }
    });




    ajax_data = { 'group_id': $("#group_id").val() };                   
    $.ajax({
        type: "POST", url: '/ajax_getemotions', dataType: 'json', data: ajax_data,
        success: function (data) {
            labels = Object.keys(data)
            values = Object.values(data)


            console.log('heere',labels,values)
            console.log('data',data)

            Highcharts.chart('bar_emotions', {
                title: {
                    text: ''
                },
                xAxis: {
                    categories: labels,
                    crosshair: true,
                },
                yAxis: {
                    title:{
                    text: 'Occurrences'
                    }
                },
                series: [{
                    name: 'emotions',
                    type: 'column',
                    data: values,
                    color:'#00b0af'

                }],
            });
        }
    });


    ajax_data = { 'group_id': $("#group_id").val() };
                            
    $.ajax({
        type: "POST", url: '/ajax_getsentiment', dataType: 'json', data: ajax_data,
        success: function (data) {
            labels = Object.keys(data)
            values = Object.values(data)

            Highcharts.chart('bar_sentiment', {
                title: {
                    text: ''
                },
                xAxis: {
                    categories: labels,
                    crosshair: true,
                },
                yAxis: {
                    title:{
                    text: 'Occurrences'
                    }
                },
                series: [{
                    name: 'sentiments',
                    type: 'column',
                    data: values,
                    color:'#d1e97b'

                }],
            });
        }
    });

   
    var gauge1 = Gauge(
        document.getElementById("attrition"), {
        max: 100,
        dialStartAngle: -90,
        dialEndAngle: -90.001,
        value: 100,
        label: function (value) {
            return (Math.round(value * 100) / 100) + '%';
        }
    }
    );
    gauge1.setValueAnimated(((analyser.stats.lefties / analyser.stats.no_users) * 100).toFixed(1), 1);

    var gauge2 = Gauge(
        document.getElementById("joining"), {
        max: 100,
        dialStartAngle: -90,
        dialEndAngle: -90.001,
        value: 100,
        label: function (value) {
            return (Math.round(value * 100) / 100) + '%';
        }
    }
    );
    gauge2.setValueAnimated(((analyser.stats.joinies / analyser.stats.no_users) * 100).toFixed(1), 1);
};

Analyser.prototype.initiateUserStats = function(){
    analyser.initiateSearchAutocomplete();
    analyser.initiateDateRanges();
    analyser.drawUserStatsGraphs();
};

Analyser.prototype.initiateSearchAutocomplete = function(){
    $('#global_search').autocomplete({
        minChars: 3,
        serviceUrl: '/data/search',
        type: 'POST',
        dataType: 'json',
        onSelect: function(selection){
            console.log(selection);
            // show the detail of this thing
            if(selection.data.category == 'Group') url = sprintf('/group_stats/%s', selection.data.id);
            else if(selection.data.category == 'User') url = sprintf('/user_stats/%s/%s', selection.data.group_id, selection.data.user);
            else if(selection.data.category == 'File') url = sprintf('/file_stats/%s', selection.data.id);
            
            analyser.showItemStats(url);
        }
    });
};

Analyser.prototype.showItemStats = function(url){
    range = $('[name=analysis_range]').val()|| '';
    $(
        sprintf(
            "<form class='hidden-form' action='%s' method='post' style='display: none;'><input type='hidden' name='range' value='%s'><input type='hidden' name='csrfmiddlewaretoken' value='%s'></form>", 
            url, 
            range, 
            analyser.csrftoken
        )
    ).appendTo('body');
    $('.hidden-form').submit();
};

Analyser.prototype.drawUserStatsGraphs = function(){
    Highcharts.chart('categories_chart', {
        chart: {
            plotBackgroundColor: null,
            plotBorderWidth: null,
            plotShadow: false,
            type: 'pie'
        },
        title: { text: '' },
        credits: analyser.graph_credits,
        tooltip: {
            headerFormat: '',
            pointFormat: '<span style="color:{point.color}">\u25CF</span> <b> {point.name}</b><br/>' +
                'Count: <b>{point.y}</b><br/>'
        },
        plotOptions: {
            pie: {
                allowPointSelect: true,
                cursor: 'pointer',
                size: '80%',
                showInLegend: true,
                dataLabels: {
                    enabled: false,
                    crop: false,
                    format: '<b>{point.name}</b>: {point.y}',
                    connectorShape: 'crookedLine',
                    crookDistance: '90%'
                }
            }
        },
        series: [{
            // minPointSize: 10,
            // maxPointSize: 200,
            innerSize: '20%',
            // colorByPoint: true,
            credits: { enabled: false },
            // zMin: 0,
            
            name: 'information',
            data: [
                { name: 'Messages', y: analyser.stats.messages_count },
                { name: 'Images', y: analyser.stats.images_count },
                { name: 'Links', y: analyser.stats.links_count },
                { name: 'Emojis', y: analyser.stats.emojis_count }
            ]
        }]
    });

    Highcharts.chart('active_days', {
        chart: { type: 'column' },
        title: { text: ''},
        xAxis: {
            categories: analyser.stats.active_dates.dates,
            crosshair: true
        },
        credits: analyser.graph_credits,
        yAxis: {
            min: 0,
            title: {
                text: 'No of messages'
            }
        },
        tooltip: {
            headerFormat: '<span style="font-size:10px">{point.key}</span><table>',
            pointFormat: '<tr><td style="color:{series.color};padding:0">{series.name}: </td>' +
                '<td style="padding:0"><b>{point.y} messages</b></td></tr>',
            footerFormat: '</table>',
            shared: true,
            useHTML: true
        },
        plotOptions: {
            column: {
                pointPadding: 0.2,
                borderWidth: 0
            }
        },
        series: [{
            name: 'Sent Messages',
            data: analyser.stats.active_dates.messages

        }]
    });

    var gauge1 = Gauge(
      document.getElementById("group_interaction"), {
        max: 100,
        dialStartAngle: -90,
        dialEndAngle: -90.001,
        value: 100,
        label: function(value) {
          return (Math.round(value * 100) / 100) + '%';
        }
      }
    );
    gauge1.setValueAnimated(analyser.stats.grp_interaction, 1);
};

Analyser.prototype.communicationError = function(){
    analyser.destroyLoadingSpinner();
};

Analyser.prototype.showLoadingSpinner = function(loading_text='Loading...'){
    if (typeof $('body').loadingModal === "function") {
        $('body').loadingModal({
          position: 'auto',
          text: loading_text,
          color: '#fff',
          opacity: '0.7',
          backgroundColor: 'rgb(0,0,0)',
          animation: 'cubeGrid'
        });
    }
};

Analyser.prototype.destroyLoadingSpinner = function(){
    if (typeof $('body').loadingModal === "function") {
        $('body').loadingModal('destroy');
    }
};

function objectifyForm(formArray) {
    //serialize data function
    var returnArray = {};
    for (var i = 0; i < formArray.length; i++){
        returnArray[formArray[i]['name']] = formArray[i]['value'];
    }
    return returnArray;
}

analyser = new Analyser();

$(document).on('click', '.nav-deep.badili-nav .nav-item', function(){
    $(this).find('ul').toggle(1000);
});

//-- Plugin implementation
(function($) {
  $.fn.countTo = function(options) {
    return this.each(function() {
      //-- Arrange
      var FRAME_RATE = 60; // Predefine default frame rate to be 60fps
      var $el = $(this);
      var countFrom = parseInt($el.attr('data-count-from'));
      var countTo = parseInt($el.attr('data-count-to'));
      var countSpeed = $el.attr('data-count-speed'); // Number increment per second

      //-- Action
      var rafId;
      var increment;
      var currentCount = countFrom;
      var countAction = function() {              // Self looping local function via requestAnimationFrame
        if(currentCount < countTo) {              // Perform number incremeant
          $el.text(Math.floor(currentCount));     // Update HTML display
          increment = countSpeed / FRAME_RATE;    // Calculate increment step
          currentCount += increment;              // Increment counter
          rafId = requestAnimationFrame(countAction);
        } else {                                  // Terminate animation once it reaches the target count number
          $el.text(countTo);                      // Set to the final value before everything stops
          //cancelAnimationFrame(rafId);
        }
      };
      rafId = requestAnimationFrame(countAction); // Initiates the looping function
    });
  };
}(jQuery));
