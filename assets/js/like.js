$('#like-page').click(function() {
	$.ajax({
		type: "POST",
		url: "/_like",
		dataType: "json",
		data: JSON.stringify({'page': $(this).val()}),
	}).done(function (data) {
		console.log(data);
		if (data == 'like') {
			$('#likes').text(parseInt($('#likes').text()) + 1);
		} else if (data == 'creator') {
			$('#like-page').popover({
				placement: 'bottom',
				title: "Sorry",
				content: "It's understood that you like your own post.",
				trigger: 'focus'
			});
			$('#like-page').popover('show');
		} else if (data == 'liked') {
			$('#like-page').popover({
				placement: 'bottom',
				title: "Sorry",
				content: "You've already liked this page once.",
				trigger: 'focus'
			});
			$('#like-page').popover('show');
		}
	})
});