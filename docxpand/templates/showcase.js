const clamp = (num, min, max) => Math.min(Math.max(num, min), max);

$(document).ready(function() {

    $("button.rotator").on("mouseover", function(event) {
        var rotator = null;
        if(event.target.tagName == "BUTTON") {
            rotator = $(event.target);
        } else {
            rotator = $(event.target).parent();
        }
        rotator.addClass("interactive");
        if(rotator.hasClass("flipped")) {
            document.documentElement.style.setProperty('--ry-delta', "180deg");
        } else {
            document.documentElement.style.setProperty('--ry-delta', "0deg");
        }
    });

    $("button.rotator").on("mouseleave", function(event) {
        var rotator = null;
        if(event.target.tagName == "BUTTON") {
            rotator = $(event.target);
        } else {
            rotator = $(event.target).parent();
        }
        rotator.removeClass("interactive");
        document.documentElement.style.setProperty('--ry-delta', "0deg");
    });

    $("button.rotator").on("click", function(event) {
        var rotator = null;
        if(event.target.tagName == "BUTTON") {
            rotator = $(event.target);
        } else {
            rotator = $(event.target).parent();
        }
        rotator.addClass("flipping");
        timeout = setTimeout(function() {
            rotator.removeClass("flipping");
        }, 1000);

        if(rotator.hasClass("flipped")) {
            rotator.removeClass("flipped");
            document.documentElement.style.setProperty('--ry-delta', "0deg");
        } else {
            rotator.addClass("flipped");
            document.documentElement.style.setProperty('--ry-delta', "180deg");
        }
    });

    $("button.rotator").on("mousemove", function(event) {
        var rotator = null;
        if(event.target.tagName == "BUTTON") {
            rotator = $(event.target);
        } else {
            rotator = $(event.target).parent();
        }
        if(rotator.hasClass("flipping")) {
            return;
        }

        const rect = event.target.getBoundingClientRect(); // get element's current size/position
        const percent = {
            x: Math.round((100 / rect.width) * (event.clientX - rect.left)),
            y: Math.round((100 / rect.height) * (event.clientY - rect.top)),
        };
        const center = {
            x: percent.x - 50,
            y: percent.y - 50,
        };

        const max_rotation = { x: 24, y: 26 };
        const degrees = {
            x: -clamp(-center.y / 1.5, -max_rotation.x, max_rotation.x),
            y: clamp(-center.x / 1.5, -max_rotation.y, max_rotation.y),
        };
        const max_shadow = { x: 16, y: 16 };
        const shadow = {
            x: clamp(center.x / 2, -max_shadow.x, max_shadow.x),
            y: clamp(center.y / 2, -max_shadow.y, max_shadow.y),
        };

        document.documentElement.style.setProperty('--rx', degrees.x+"deg");
        document.documentElement.style.setProperty('--ry', degrees.y+"deg");
        document.documentElement.style.setProperty('--gx', percent.x+"%");
        document.documentElement.style.setProperty('--gy', percent.y+"%");
        document.documentElement.style.setProperty('--sx', shadow.x+"px");
        document.documentElement.style.setProperty('--sy', shadow.y+"px");
    });
});
