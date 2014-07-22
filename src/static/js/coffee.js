// coffee.js - Waqas Bhatti (wbhatti@astro.princeton.edu) - Jul 2014
// This contains JS to drive some parts of the astroph-coffee interface


var coffee = {

    // this handles actual voting
    vote_on_paper: function(arxivid) {

        var arxividfilter = '[data-arxivid="' + arxivid + '"]';
        var votebutton = $('.vote-button').filter(arxividfilter);
        var votetotal = $('.vote-total').filter(arxividfilter);

        // use attr instead of data since jquery only knows about the first-ever
        // value on page-load and uses that for .data()
        var votetype = votebutton.attr('data-votetype');

        console.log(votetype + ' vote fired on ' + arxivid);

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

                       // update the button to show that we've voted
                       if (votetype == 'up') {

                           votebutton
                               .addClass('alert')
                               .html('Remove your vote for this paper')
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
                       messagebar.html(alertbox).fadeIn('fast').fadeOut(7500);
                       $(document).foundation();

                   }


               },
               'json').fail(function (data) {

                   var alertbox =
                       '<div data-alert class="alert-box alert radius">' +
                       'Something went wrong with the server, ' +
                       'please <a href="/astroph-coffee/about">' +
                       'let us know</a> about this problem!' +
                       '<a href="#" class="close">&times;</a></div>'
                   messagebar.html(alertbox);
                   $(document).foundation();

               });

    },


    // sets up all event bindings
    action_setup: function () {

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

    }

};
