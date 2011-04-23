//
// Douglas Crockford douglas@crockford.com snippet
//
// See: http://javascript.crockford.com/remedial.html
//

if(!String.prototype.supplant) {
  //
  // Douglas Crockford douglas@crockford.com snippet
  //
  String.prototype.supplant = function (o) {
    return this.replace(/{([^{}]*)}/g,
                        function (a, b) {
                          var r = o[b];
                          return typeof r === 'string' || typeof r === 'number' ? r : a;
                        }
                       );
  };
 }
