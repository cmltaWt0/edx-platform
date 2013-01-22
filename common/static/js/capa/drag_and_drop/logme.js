// Wrapper for RequireJS. It will make the standard requirejs(), require(), and
// define() functions from Require JS available inside the anonymous function.
//
// See https://edx-wiki.atlassian.net/wiki/display/LMS/Integration+of+Require+JS+into+the+system
(function (requirejs, require, define) {

define([], function () {
    var debugMode;

    debugMode = true;

    return logme;

    function logme() {
        var i;

        if (
            (debugMode !== true) ||
            (typeof window.console === 'undefined')
        ) {
            return;
        }

        i = 0;
        while (i < arguments.length) {
            window.console.log(arguments[i]);
            i += 1;
        }
    }
});

// End of wrapper for RequireJS. As you can see, we are passing
// namespaced Require JS variables to an anonymous function. Within
// it, you can use the standard requirejs(), require(), and define()
// functions as if they were in the global namespace.
}(RequireJS.requirejs, RequireJS.require, RequireJS.define)); // End-of: (function (requirejs, require, define)
