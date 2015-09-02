// coffee.js - Waqas Bhatti (wbhatti@astro.princeton.edu) - Jul 2014
// This contains JS to drive some parts of the astroph-coffee interface


var coffee = {

    // this handles actual voting
    vote_on_paper: function(arxivid) {

        // filter DOM for what we want
        var arxividfilter = '[data-arxivid="' + arxivid + '"]';
        var votebutton = $('.vote-button').filter(arxividfilter);
        var votetotal = $('.vote-total').filter(arxividfilter);
        var votepostfix = $('.vote-postfix').filter(arxividfilter);
        var presenters = $('.article-presenters').filter(arxividfilter);

        // use attr instead of data since jquery only knows about the first-ever
        // value on page-load and uses that for .data()
        var votetype = votebutton.attr('data-votetype');

        var xsrftoken = $('#voting-form input').val();
        var messagebar = $('#message-bar');

        $.post('/astroph-coffee/vote',
               {arxivid: arxivid,
                votetype: votetype,
                _xsrf: xsrftoken},
               function(data) {

                   if (data.status == 'success') {

                       // update the vote total for this arxivid
                       votetotal.text(data.results['nvotes']);
                       if (data.results['nvotes'] != 1) {
                           votepostfix.text('votes')
                       }
                       else {
                           votepostfix.text('vote')
                       }

                       // update the button to show that we've voted
                       if (votetype == 'up') {

                           votebutton
                               .addClass('alert')
                               .html('Remove your vote')
                               .attr('data-votetype','down');

                       }

                       else if (votetype == 'down') {

                           votebutton
                               .removeClass('alert')
                               .html('Vote for this paper')
                               .attr('data-votetype','up');

                       }

                   }

                   else {

                       var message = data.message;
                       var alertbox =
                           '<div data-alert class="alert-box warning radius">' +
                           message +
                           '<a href="#" class="close">&times;</a></div>'
                       messagebar.html(alertbox).fadeIn(52).fadeOut(8000);
                       $(document).foundation();

                   }


               },
               'json').fail(function (data) {

                   var alertbox =
                       '<div data-alert class="alert-box alert radius">' +
                       'Uh oh, something went wrong with the server, ' +
                       'please <a href="/astroph-coffee/about">' +
                       'let us know</a> about this problem!' +
                       '<a href="#" class="close">&times;</a></div>'
                   messagebar.html(alertbox);
                   $(document).foundation();

               });

    },


    // this stores the current view settings to a cookie
    store_cookie_settings: function () {

        // get current settings
        var view = [];

        $('#show-local-check,#show-voted-check,#show-other-check')
            .each(function (ind, elem) {
                view.push(elem.checked);
            });

        var fontsize = $('[name="font-size-radio"]')
            .filter(':checked')
            .attr('id');

        // store in a cookie
        $.cookie('coffee_settings',{view:view, fontsize:fontsize}, {expires:30});

    },

    // this restores the cookied view settings
    restore_cookie_settings: function () {

        // get the settings from the cookie
        var viewsettings = $.cookie('coffee_settings');

        var viewcontrols = ['#show-local-check',
                            '#show-voted-check',
                            '#show-other-check'];

        if (typeof viewsettings != 'undefined') {

            // set the view options
            viewcontrols.forEach(function (e,i,a) {

                // check the controls
                if (viewsettings.view[i] == true) {

                    $(viewcontrols[i]).prop('checked',true);
                    // set the properties
                    if (i == 0) {
                        $('.local-paper-listing .paper-abstract')
                            .slideDown('fast');
                    }
                    else if (i == 1) {
                        $('.voted-paper-listing .paper-abstract')
                            .slideDown('fast');
                    }
                    else if (i == 2) {
                        $('.other-paper-listing .paper-abstract')
                            .slideDown('fast');
                    }

                }
                else {

                    $(viewcontrols[i]).prop('checked',false);
                    // set the properties
                    if (i == 0) {
                        $('.local-paper-listing .paper-abstract')
                            .slideUp('fast');
                    }
                    else if (i == 1) {
                        $('.voted-paper-listing .paper-abstract')
                            .slideUp('fast');
                    }
                    else if (i == 2) {
                        $('.other-paper-listing .paper-abstract')
                            .slideUp('fast');
                    }
                }


            });

            // set the controls
            $('#' + viewsettings.fontsize).click();

            // set the font options
            if (viewsettings.fontsize == 'font-size-small') {

                $('.paper-abstract p')
                    .removeClass('abstract-para-medium')
                    .removeClass('abstract-para-large')
                    .addClass('abstract-para-small');

            }

            else if (viewsettings.fontsize == 'font-size-medium') {

                $('.paper-abstract p')
                    .removeClass('abstract-para-large')
                    .removeClass('abstract-para-small')
                    .addClass('abstract-para-medium');

            }

            else if (viewsettings.fontsize == 'font-size-large') {

                $('.paper-abstract p')
                    .removeClass('abstract-para-small')
                    .removeClass('abstract-para-medium')
                    .addClass('abstract-para-large');

            }

        }

    },

    // sets up all event bindings
    action_setup: function () {

        // cookie settings
        $.cookie.json = true;
        coffee.restore_cookie_settings();

        // handle sliding out the abstract when the paper title is clicked
        $('.paper-title').on('click', function(evt) {

            evt.preventDefault();
            var arxivid = $(this).data('arxivid');
            var abstractfilter = '[data-arxivid="' + arxivid + '"]';
            var abstractelem = $('.paper-abstract').filter(abstractfilter);
            abstractelem.slideToggle('fast');

        });

        // handle clicking on the vote button
        $('.vote-button').on('click', function(evt) {

            var arxivid = $(this).data('arxivid');
            evt.preventDefault();
            coffee.vote_on_paper(arxivid);

        });

        // handle clicking on the various view options
        $('#preferences-pane').on('click','#show-local-check',function (evt) {

            if ($(this).prop('checked') == true) {
                $('.local-paper-listing .paper-abstract').slideDown('fast');
            }
            else {
                $('.local-paper-listing .paper-abstract').slideUp('fast');
            }
            coffee.store_cookie_settings();

        });

        // handle clicking on the various view options
        $('#preferences-pane').on('click','#show-voted-check',function (evt) {

            if ($(this).prop('checked') == true) {
                $('.voted-paper-listing .paper-abstract').slideDown('fast');
            }
            else {
                $('.voted-paper-listing .paper-abstract').slideUp('fast');
            }
            coffee.store_cookie_settings();

        });

        // handle clicking on the various view options
        $('#preferences-pane').on('click','#show-other-check',function (evt) {

            if ($(this).prop('checked') == true) {
                $('.other-paper-listing .paper-abstract').slideDown('fast');
            }
            else {
                $('.other-paper-listing .paper-abstract').slideUp('fast');
            }
            coffee.store_cookie_settings();

        });

        // handle clicking on the various font options
        $('#preferences-pane').on('click','#font-size-small',function (evt) {

            $('.paper-abstract p')
                .removeClass('abstract-para-medium')
                .removeClass('abstract-para-large')
                .addClass('abstract-para-small');
            coffee.store_cookie_settings();

        });

        // handle clicking on the various font options
        $('#preferences-pane').on('click','#font-size-medium',function (evt) {

            $('.paper-abstract p')
                .removeClass('abstract-para-small')
                .removeClass('abstract-para-large')
                .addClass('abstract-para-medium');
            coffee.store_cookie_settings();

        });

        // handle clicking on the various font options
        $('#preferences-pane').on('click','#font-size-large',function (evt) {

            $('.paper-abstract p')
                .removeClass('abstract-para-small')
                .removeClass('abstract-para-medium')
                .addClass('abstract-para-large');
            coffee.store_cookie_settings();

        });


    }

};
