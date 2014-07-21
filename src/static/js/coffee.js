// coffee.js - Waqas Bhatti (wbhatti@astro.princeton.edu) - Jul 2014
// This contains JS to drive some parts of the astroph-coffee interface


var coffee = {

    action_setup: function () {

        $('.paper-title').on('click', function(evt) {
            evt.preventDefault();
            var arxivid = $(this).data('arxivid');
            var abstractfilter = '[data-arxivid="' + arxivid + '"]';
            var abstractelem = $('.paper-abstract').filter(abstractfilter);
            abstractelem.slideToggle('fast');
        });

    }

};
