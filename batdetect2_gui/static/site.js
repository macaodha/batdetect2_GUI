// this will cause problems if number of individuals is large
function ind_color(ind) {
  var ind_colors = ['red', 'blue', 'green', 'yellow', 'purple', 'pink', 'orange', 'brown', 'white', 'black'];
  if (ind < ind_colors.length-1) {
    return ind_colors[ind];
  }
  else {
    // hack: this wont produce varied colors but will allow > len(ind_colors)
    var c = (ind & 0x00FFFFFF).toString(16).toUpperCase();
    return "#" + ("00000".substring(0, 6 - c.length) + c);
  }
}

// https://stackoverflow.com/questions/1484506/random-color-generator
function str_to_rgb(ip_str){
  // string to num
  var hash = 0;
  for (var i = 0; i < ip_str.length; i++) {
     hash = ip_str.charCodeAt(i) + ((hash << 5) - hash);
  }

  // num to color
  var c = (hash & 0x00FFFFFF).toString(16).toUpperCase();
  return "#" + ("00000".substring(0, 6 - c.length) + c);
}

var jcrop_api;

/**
 * container for everything
 */
var app = function () {

    return {

        /**
        * before submitting the paths, saves them to local storage so that we don't have to keep pasting them
        * if things crash, need to be restarted
        */
        savePaths: function () {

           localStorage.setItem('audio_dir', $('input[name=audio_dir]')[0].value);
           localStorage.setItem('annotation_dir', $('input[name=annotation_dir]')[0].value);

        },

        /**
         * Called when page loads
         */
        filelist_init: function () {

            //populate fields from locally cached
            // this is done on the client so we can restart the webserver without losing the data
            if ($('input[name=audio_dir]').length > 0) {
                $('input[name=audio_dir]')[0].value = localStorage.getItem('audio_dir');
                $('input[name=annotation_dir]')[0].value = localStorage.getItem('annotation_dir');
            }

            $('form a.clear').click(function () {
                $(this).closest('form').find('input').val('');
                return false;
            });

        },

        /**
         * Initializes the annotation stuff
         * Called when the page loads
         */
        annotate_init: function () {

            app.change_made(false);

            // if the spec well (container) is wider than the spec width (true for short recordings), set its width to
            // the spec width  (otherwise it will just be the container/screen width I guess)
            if (parseInt($(".spec_well").css("width")) > spec_width) {
              $(".spec_well").css("width", spec_width);
              $(".right_axis").css("left", spec_width + parseInt($(".right_axis").css("width")) );
            }
            $("#progress").css('width', spec_width);


            // set up jcrop

            // Some fixed/default opts, some of which are overriden by embedded js based on template values
            var jcrop_default_opts = {
                    // these settings will end up in jcrop_api.opt.
                    multi: true,
                    event_name: "Echolocation",
                    individual_id: '0',
                    class_name: 'unknown',
                    //onChange: update_label_info, // called when selection is completed, if added back change_made will not work
                    onSelect: update_label_info    // called when the selection is moving
                };

            // merge in opts to the defaults
            Object.assign(jcrop_default_opts, jcrop_opts);


            jQuery(function($) {
                $('#spec_im').Jcrop(jcrop_default_opts, function () {
                    jcrop_api = this;
                    // draw the existing bounding boxes
                    jcrop_items.forEach(function (item) {
                        jcrop_api.newSelection();
                        app.update_box_colors(item.class, parseInt(item.individual));
                        jcrop_api.setSelect(app.time_freq_to_coords(item.start_time,
                                                            item.end_time,
                                                            item.high_freq,
                                                            item.low_freq,
                                                            file_params.fft_win_length_secs,
                                                            file_params.sampling_rate,
                                                            file_params.fft_overlap,
                                                            file_params.spec_height,
                                                            file_params.spec_width));
                        jcrop_api.ui.selection.class_name    = item.class;
                        jcrop_api.ui.selection.event_name    = item.event;
                        jcrop_api.ui.selection.individual_id = item.individual.toString();
                        jcrop_api.refresh();
                    });
                });
            });

            // events, mainly just to detect and register ay change change
            $("#notes").change(function(){
              app.change_made();
            });

            $("#unsure").change(function(){
              app.change_made();
            });

            $("#class_select").change(function(){
              app.change_made();
              if (jcrop_api.ui.selection != null) {
                jcrop_api.ui.selection.class_name = $("#class_select").val();
                jcrop_api.opt.class_name = $("#class_select").val();
                app.update_box_colors(jcrop_api.ui.selection.class_name, parseInt(jcrop_api.ui.selection.individual_id));
              }
            });

            $("#event_select").change(function(){
              app.change_made();
              if (jcrop_api.ui.selection != null) {
                jcrop_api.ui.selection.event_name = $("#event_select").val();
                jcrop_api.opt.event_name = $("#event_select").val();
                app.update_box_colors(jcrop_api.ui.selection.class_name, parseInt(jcrop_api.ui.selection.individual_id));
              }
            });

            $("#individual_id_select").change(function(){
              app.change_made();
              if (jcrop_api.ui.selection != null) {
                jcrop_api.ui.selection.individual_id = $("#individual_id_select").val();
                jcrop_api.opt.individual_id = $("#individual_id_select").val();
                app.update_box_colors(jcrop_api.ui.selection.class_name, parseInt(jcrop_api.ui.selection.individual_id));
              }
            });


            // audio playing
            var my_audio = document.getElementById('player');
            var ctrl = document.getElementById('audio_control');
            var prog = document.getElementById('progress');

            // update the info when user clicks on a box
            function update_label_info(c) {

              if (jcrop_api.ui.selection != null) {
                app.change_made();
                app.update_box_colors(jcrop_api.ui.selection.class_name, parseInt(jcrop_api.ui.selection.individual_id));
                $('#class_select').val(jcrop_api.ui.selection.class_name);
                $('.selectpicker').selectpicker('refresh');
                //$("#class_select").val(jcrop_api.ui.selection.class_name);
                $("#event_select").val(jcrop_api.ui.selection.event_name);
                $("#individual_id_select").val(jcrop_api.ui.selection.individual_id);


              }

              app.print_box_info();

            };

            // for keyboard press - ind is a string
            function update_individual_id(ind) {
              app.change_made();
              if (jcrop_api.ui.selection != null) {
                jcrop_api.ui.selection.individual_id = ind;
                jcrop_api.opt.individual_id = ind;
                $("#individual_id_select").val(ind);
                app.update_box_colors(jcrop_api.ui.selection.class_name, parseInt(jcrop_api.ui.selection.individual_id));
              }
            }

            // get the click on the progress bar
            prog.addEventListener('click', function (e) {

              var click_pos = (e.pageX - e.target.getBoundingClientRect()['left']) / this.offsetWidth;

              // var click_pos = (e.pageX - this.offsetLeft) / this.offsetWidth;
              // console.log('b', my_audio.currentTime, click_pos*my_audio.duration);
              //my_audio.currentTime = click_pos*my_audio.duration;
              my_audio.currentTime = click_pos * file_params.duration_listen;
              my_audio['play']();

              ctrl.innerHTML = 'pause';
            });

            ctrl.addEventListener('click', function () {
              // update the button
              var pause = ctrl.innerHTML == 'pause';
              ctrl.innerHTML = pause ? 'play' : 'pause';

              // update the audio
              var method = pause ? 'pause' : 'play';
              my_audio[method]();
            });

            // timeupdate audio event happens all the time
            // update the time display and the horizontal scroll based on the audio time
            my_audio.addEventListener('timeupdate', function() {
                $("#current_time").html((my_audio.currentTime).toFixed(3) + ' secs');
                //var fraction_complete = my_audio.currentTime / my_audio.duration;
                var fraction_complete = my_audio.currentTime / file_params.duration_listen;
                var percent_complete = 100*Number((fraction_complete).toFixed(5));

                // make scroll window follow audio
                var scroll_pos = fraction_complete*$('#spec_im').width();
                scroll_pos = Math.max(scroll_pos-$('.spec_well').width()/2.0,0);
                $('.spec_well').scrollLeft(scroll_pos);

                // update progress bar
                $("#progress-bar").css("width", percent_complete + "%").attr("aria-valuenow", percent_complete);

                // when file finished playing allow restart
                if (percent_complete == 1) {
                    ctrl.innerHTML = 'play';
                }
            });

            // prevent space key press from moving browser scroll bar
            document.documentElement.addEventListener('keydown', function (e) {
                if ( (( e.keycode || e.which ) == 32) && !$("#notes").is(':focus') ) {
                    e.preventDefault();
                }
            }, false);


            // keyboard shortcuts
            $(document).keydown(function(e) {
              //console.log(e.which);

              if ($("#class_select").data('selectpicker').$searchbox.is(':focus') && e.which === 13) {
                  console.log("item not in list, add it?");

                  // the value the user has typed in
                  var new_item_value = $("input", ".dropdown-menu").val();
                  // add the value to the list of labels
                  $("#class_select").append('<option data-tokens="'+new_item_value+'" selected="selected">'+new_item_value+'</option>');
                  // refresh the select picker from the updated option list
                  $("#class_select").selectpicker("refresh");
                  // ensure the selected val is correct
                  $("#class_select").selectpicker('val', new_item_value);
                  // trigger the change function so that this value is saved to the annotation list
                  $("#class_select").change();

              }

              //if ((!$("#notes").is(':focus')) && (!$("#class_select").is(':focus'))) {
              if ((!$("input").is(':focus')) && (!$("#notes").is(':focus')) && (!$("#class_select").data('selectpicker').$searchbox.is(':focus'))) {


                    // space bar - play audio
                    if(e.which == 32)
                      $('#audio_control').click();

                    // r - reset audio to beginning
                    if(e.which == 82)
                      my_audio.currentTime = 0

                    // s - submit annotation
                    if(e.which == 83)
                      $('#submit_btn').click();

                    // u - unsure
                    if(e.which == 85) {
                      if ($('#unsure').is(':checked') == true) {
                        $('#unsure').prop('checked', false);
                      }
                      else {
                        $('#unsure').prop('checked', true);
                      }
                    }

                    // numbers for individual id
                    if((e.which >= 48) && (e.which <= 57))
                      update_individual_id(''+(e.which-48))

                    // c - move scroll forward
                    if(e.which == 67)
                      $('.spec_well').scrollLeft($('.spec_well').scrollLeft() + 100);

                    // z - move scroll forward
                    if(e.which == 90)
                      $('.spec_well').scrollLeft($('.spec_well').scrollLeft() - 100);

              }

            });


            $("#spectrogram_params input").change(function(){
                app.validate_spectrogram_params();
            });

            $("#spectrogram_params button").hover(function(){
                app.validate_spectrogram_params();
            });

            // add the frequency axis
            app.freq_axis();
            app.box_toggle_init();
            app.convert_win_length_units();

            $("#win_length_units").change(function () {
                if ($(this).val() === 'seconds') {
                    app.convert_win_length_units(null, $('#fft_win_length').val());

                } else {
                    app.convert_win_length_units($('#fft_win_length').val(), null);
                }
            });

            app.validate_spectrogram_params();

        },

        /**
         *  converts a value from the given units (seconds or samples)
         *  into the other set of units, updating the relevant dom elements
         *  @returns object: seconds, samples
         */
        convert_win_length_units: function (val_seconds, val_samples) {

            var units = $('#win_length_units').val();

            if (!$.isNumeric(val_seconds) && !$.isNumeric(val_samples)) {
                if (units === 'seconds') {
                    val_seconds = $('#fft_win_length').val();
                } else {
                    val_samples = $('#fft_win_length').val();
                }
            }

            if ($.isNumeric(val_seconds)) {
                val_samples = Math.round(val_seconds * file_params.sampling_rate)
            } else if ($.isNumeric(val_samples)) {
                val_seconds = val_samples / file_params.sampling_rate;
            }

            if (units === 'seconds') {
              // smallest (though impractical) window size would be 2 samples
              var step = 2 / file_params.sampling_rate;
              $('#fft_win_length').val(val_seconds);
              $('#win_length_other').html(val_samples + " samples");
//              $('#fft_win_length').attr('step', step)
//              $('#fft_win_length').attr('min', step)
            } else {
              $('#fft_win_length').val(val_samples);
              $('#win_length_other').html(val_seconds + " seconds");
//              $('#fft_win_length').attr('step', 1)
//              $('#fft_win_length').attr('min', 2)
            }

            return {
                seconds: val_seconds,
                samples: val_samples
            }

        },


        validate_spectrogram_params: function () {

            var errors = [];
            var warnings = []

            // window length
            var win_length = app.convert_win_length_units();


            if (!Number.isInteger(Math.log2(win_length.samples))) {
                warnings.push("fft_win_length: Powers of 2 are faster to compute");
            }
            if (win_length.samples < 2) {
                errors.push['fft_win_length is too low']
            }

            // overlap
            var overlap = $('#fft_overlap').val()

            if (overlap >= 1) {
                // actual maximum overlap would be window-size in samples minus one
                // but, since we don't know the sample rate of other files, and window size may be set in seconds
                // we won't worry about that here, but rather validate per file when generating spectrogram
                errors.push("fft_overlap must be less than 1");
            }
            if (overlap < 0) {
                // we can actually do a negative overlap and it works, so we won't require it to be non-negative
                warnings.push("fft_overlap is less than zero, meaning we skip some samples every time-frame");
            }

            $("#spectrogram_params_warnings").html(warnings.join('<br>')).css(warnings.length ? 'block' : 'none');
            $("#spectrogram_params_errors").html(errors.join('<br>')).css(errors.length ? 'block' : 'none');

            return errors.length === 0;

        },

        /**
         * convert time (start and end) and freq (high and low) to
         * pixel offset from bottom left, and height and width
         * arguments for the fft are used to calculate this
         */
        time_freq_to_coords: function(start_time, end_time, high_freq, low_freq, fft_win_length_secs, fs, fft_overlap, spec_height, spec_width) {
            // converts time frequency annotations into bounding boxes
            var st = app.time_to_x_coords(start_time, fs, fft_win_length_secs, fft_overlap);
            var en = app.time_to_x_coords(end_time, fs, fft_win_length_secs, fft_overlap);
            var width = en - st;
            var height = fft_win_length_secs*(high_freq - low_freq);
            var low = spec_height - fft_win_length_secs*low_freq - height
            return [st, low, width, height];
        },

        /**
         * convert a horizonal pixel offset to a time
         */
        x_coords_to_time: function(x_pos, fs, fft_win_length_secs, fft_overlap) {
            var nfft = Math.floor(fft_win_length_secs*fs);
            var noverlap = Math.floor(fft_overlap*nfft);
            return ((x_pos*(nfft - noverlap)) + noverlap)/fs;
        },

        /**
         * convert a time (s?) to pixel offset
         */
        time_to_x_coords: function (tm, fs, fft_win_length_secs, fft_overlap) {
            var nfft = Math.floor(fft_win_length_secs*fs);
            var noverlap = Math.floor(fft_overlap*nfft);
            return (tm*fs-noverlap)/(nfft - noverlap);
        },

        /**
         * collects all the user inputs (fields for each annotation) and puts them in an array
         */
        get_output: function() {
            console.log("clicked submit");

            // constants for converting back coords
            var spec_height = file_params.spec_height;
            var fft_win_length_secs = file_params.fft_win_length_secs;
            var fft_overlap = file_params.fft_overlap;
            var fs = file_params.sampling_rate;

            var result_annotation = [];
            for (var ii = 0; ii < jcrop_api.ui.multi.length; ii++) {
                var res_dict = {};
                //res_dict['coords'] = [jcrop_api.ui.multi[ii].last.x, jcrop_api.ui.multi[ii].last.y, jcrop_api.ui.multi[ii].last.w, jcrop_api.ui.multi[ii].last.h];
                res_dict['start_time'] = app.x_coords_to_time(jcrop_api.ui.multi[ii].last.x, fs, fft_win_length_secs, fft_overlap);
                res_dict['end_time'] = app.x_coords_to_time(jcrop_api.ui.multi[ii].last.x + jcrop_api.ui.multi[ii].last.w, fs, fft_win_length_secs, fft_overlap);
                // TODO this only works if params['min_freq'] == 0
                res_dict['high_freq'] = (-jcrop_api.ui.multi[ii].last.y+spec_height)/fft_win_length_secs;
                res_dict['low_freq'] = res_dict['high_freq'] - jcrop_api.ui.multi[ii].last.h/fft_win_length_secs;
                res_dict['class'] = jcrop_api.ui.multi[ii].class_name;
                res_dict['event'] = jcrop_api.ui.multi[ii].event_name;
                res_dict['individual'] = jcrop_api.ui.multi[ii].individual_id;
                result_annotation.push(res_dict);
            }

            $("#updated_annotations").val(JSON.stringify(result_annotation));
        },

        change_made: function (val = true) {
            $("#change_made").val(JSON.stringify(val));
        },

        /**
         * displays the audio information and selected annotation information
         */
        print_box_info: function() {

            if (jcrop_api.ui.selection !== null) {
                var spec_height = file_params.spec_height;
                var fft_win_length_secs = file_params.fft_win_length_secs;
                var fft_overlap = file_params.fft_overlap;
                var fs = file_params.sampling_rate;

                var start_time = app.x_coords_to_time(jcrop_api.ui.selection.last.x, fs, fft_win_length_secs, fft_overlap);
                var end_time   = app.x_coords_to_time(jcrop_api.ui.selection.last.x + jcrop_api.ui.selection.last.w, fs, fft_win_length_secs, fft_overlap);
                var high_freq  = (-jcrop_api.ui.selection.last.y+spec_height)/fft_win_length_secs;
                var low_freq   = high_freq - jcrop_api.ui.selection.last.h/fft_win_length_secs;

                $("#box_duration").html((end_time-start_time).toFixed(3) + ' secs');
                $("#box_low_freq").html((low_freq).toFixed(2) + ' Hz');
                $("#box_high_freq").html((high_freq).toFixed(2) + ' Hz');
                $("#box_info").show();
                $("#none_selected").hide();

            } else {
                $("#box_info").hide();
                $("#none_selected").show();

            }


        },


        // updates the css of the jcrop box depending on whether it's selected etc.
        update_box_colors: function (class_name, individual_id) {
            $("div.jcrop-selection.jcrop-current div.jcrop-handle.jcrop-drag.ord-ne").css("border", "5px solid " + str_to_rgb(class_name));

            if (individual_id != -1) {
            $("div.jcrop-selection.jcrop-current div.jcrop-handle.jcrop-drag.ord-se").css("border", "5px solid " + ind_color(individual_id));
            }
            else {
            $("div.jcrop-selection.jcrop-current div.jcrop-handle.jcrop-drag.ord-se").css("border", "");
            }
        },

        /**
          draw the frequency axis
        */
        freq_axis: function () {

            // extra 20px so the zero can overhang the bottom.
            $('.axis').css('height', file_params.spec_height + 20 + 'px');
            var max = spectrogram_params.max_freq;
            var px_per_hz = file_params.spec_height / spectrogram_params.max_freq;
            // minimum distance between ticks
            var min_gap_px = 80;
            var min_gap_hz = min_gap_px / px_per_hz;
            var exp = Math.floor(Math.log10(min_gap_hz));
            var sig = Math.ceil(min_gap_hz / Math.pow(10, exp));
            var tick_every_hz = sig * Math.pow(10, exp);
            var num_ticks = Math.floor(spectrogram_params.max_freq / tick_every_hz) + 1;
            var tick_positions = Array.from(Array(num_ticks)).map((cur, i) => i * tick_every_hz / spectrogram_params.max_freq);
            // top tick is always exactly the top
            // add a new one if the last one is not too close, otherwise move the last one to the top
            var dist_to_top = (spectrogram_params.max_freq % tick_every_hz) * px_per_hz
            if (dist_to_top < 20) {
                tick_positions[tick_positions.length - 1] = 1;
            } else {
                tick_positions.push(1);
            }

            tick_positions.forEach(pos => {
                var vpos = file_params.spec_height * (1-pos);
                el = $('<div></div>').appendTo('.axis');
                $(el).css('top', vpos+'px').html( Math.round(pos * max /100) / 10 + ' kHz');
            });

        },

        /**
         * sets up the ui for any show/hide box content
         */
        box_toggle_init: function () {

            $('.box_content').each(function (el) {

                var box_content = $(this);
                var container = $(box_content.closest('.box_section'));

                $('<span></span>').appendTo($('.box_heading', container))
                  .addClass('toggle fa')
                  .click(function() {
                      $(box_content).toggle(100);
                      $(container).toggleClass('off');
                  });

            });



        }


  };

}();


